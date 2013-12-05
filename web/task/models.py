# -*- coding: utf-8 -*-
import time, datetime, urllib2, sys, json
from dateutil.tz import gettz
import logging
reload(sys)
sys.setdefaultencoding('utf-8')
from redis import StrictRedis

from django.utils.timezone import utc
from django.db import models
from django.conf import settings

from apscheduler.triggers import CronTrigger, DateTrigger, IntervalTrigger
from apscheduler.job import Job

from mycron.task.jobstore import JobStore, JobSync, JobStats


logger = logging.getLogger('cron.frontend')



class TaskManager(models.Manager):
    def __init__(self, *args, **kwargs):
        self.timezone = gettz('Asia/Chongqing')
        self._redis = None
        self._job_sync = None
        self._job_store = None
        self._job_stats = None
        super(TaskManager, self).__init__(*args, **kwargs)

    @property
    def redis(self):
        if not self._redis:
            try:
                self._redis = StrictRedis(**settings.REDISES['default'])
            except:
                logger.exception('cannot connect to reddis')
                raise
        return self._redis

    @property
    def job_store(self):
        if not self._job_store:
            self._job_store = JobStore(self.redis)
        return self._job_store

    @property
    def job_sync(self):
        if not self._job_sync:
            self._job_sync = JobSync(self.redis)
        return self._job_sync

    @property
    def job_stats(self):
        if not self._job_stats:
            self._job_stats = JobStats(self.redis)
        return self._job_stats

    def search(self, keywords):
        return self.filter(models.Q(name__contains=keywords) | models.Q(run_entry__contains=keywords))

    def now(self):
        return datetime.datetime.now(self.timezone)


task_type_choices = (
    ('date', '单次任务'),
    ('interval', '间隔任务'),
    ('cron', 'CRON-Like任务'),
)

class Task(models.Model):
    name        = models.CharField('任务名称', max_length   = 64, default='')
    discription = models.TextField('任务描述', default='', blank=True)
    active      = models.BooleanField('是否启用', default=1)
    type        = models.CharField('任务类型', max_length   = 16, default='interval', choices=task_type_choices)

    create_at   = models.DateTimeField('创建时间', auto_now_add = True, editable=False)
    update_at   = models.DateTimeField('更新时间', auto_now = True, editable=False)
    create_by   = models.CharField('创建用户', max_length   = 64, default='unkown', editable=False)

    run_entry   = models.URLField('请求地址', max_length   = 255, help_text="填写任务的请求url，并选择通过GET还是POST方式请求")
    run_type    = models.CharField('请求方式', max_length   = 16, default='GET', choices=(('get','GET') , ('post', 'POST')))
    run_params  = models.TextField('请求参数', default='', blank=True)
    run_host    = models.IPAddressField('请求主机', max_length=16, default='', blank=True) 

    run_time    = models.CharField('运行时间', max_length=255)

    runs        = models.IntegerField('运行次数', default=0, editable=False)
    fails       = models.IntegerField('失败次数', default=0, editable=False)

    trigger     = None
    objects     = TaskManager()
    next_run_time = 0

    class Meta:
        app_label='task'

    def enable(self, *args, **kwargs):
        if self.active == 1:
            return
        self.active = 1
        self.save(*args, **kwargs)

    def disable(self, *args, **kwargs):
        if self.active == 0:
            return
        self.active = 0
        self.save(*args, **kwargs)


    def save(self, *args, **kwargs):
        '''
        1. 插入新记录，需要将task加入到待运行任务池中
        2. 如果是状态改变，不要用直接调用save方法。 请调用enable|disable方法
        3. 如果插入mysql成功，但修改job_store失败，需要对mysql操作进行回滚
        '''

        sync = None
        action = 'update' if self.id > 0 else "insert"
        if not self.validate():
            return None

        if action == 'update':
            raw_task = Task.objects.get(pk=self.id)
            # delete job
            raw_active = raw_task.isActive()
            cur_active = self.isActive()
            if raw_active:
                sync = "update" if cur_active else "remove"
            else:
                sync = "add" if cur_active else None
        else:
            if self.isActive():
                sync = "add"

        super(self.__class__, self).save(*args, **kwargs)
        logging.info('save task %s %s' % (action, str(self)))

        try:
            if sync:
                job = self.getJob()
                Task.objects.job_sync.push(self.id, sync, job)
        except:
            logger.exception('sync job(id=%d, sync=%s) to job cache failed' % (self.id, sync))

    def delete(self, *args, **kwargs):
        job_id = self.id
        job    = self.getJob()
        super(self.__class__, self).delete(*args, **kwargs)
        logging.info('delete task manual '+ str(self))
        Task.objects.job_sync.push(job_id, 'remove', job)


    def getJob(self):
        trigger = self.getTrigger()
        kwargs = {'method':self.run_type, 'params':self.run_params, 'host': self.run_host, "id":self.id}
        job = Job(self.id, trigger, self.run_entry, [], kwargs, 1, None, str(self.name), None, 1)
        return job


    def getTriggerArgs(self):
        if self.type == 'interval':
            args = json.loads(self.run_time)
            #args = {key:int(value) for value, key in intervals.split()}
        elif self.type == 'date':
            run_date  = datetime.datetime.strptime(self.run_time, '%Y-%m-%d %H:%M:%S')
            args = [run_date]
        elif self.type == 'cron':
            names  = ['second', 'minute', 'hour', 'day_of_week', 'day', 'month', 'year']
            fields = [field.strip() for field in self.run_time.split()]
            args = dict(zip(names, fields))
        else:
            pass
        return args

            
    def isActive(self):
        now = datetime.datetime.now(Task.objects.timezone)
        return self.active == 1 and self.compute_next_run_time(now) is not None

    @property
    def status(self):
        # 检查任务状态，禁用? 过期，完成？正常
        job = Task.objects.job_store.find_job(self.id)
        if not self.active:
            status = "disabled"
        if job:
            status = "normal"
        else:
            status = "finished"
        return status
        
    @property
    def stats(self):
        # 成功率，失败率，miss率

        times = Task.objects.job_stats.get(self.id)
        success = int(times.get('success', 0))
        missed  = int(times.get('missed', 0))
        failed  = int(times.get('failed', 0))
        total = success + missed + failed
        if total == 0:
            success_rate = 0.0
            failed_rate = 0.0
            missed_rate = 0.0
        else:
            success_rate = success * 100.0 /total 
            failed_rate = failed * 100.0 /total 
            missed_rate = missed * 100.0 /total 

        return {
            "total"        : total,
            "success"      : success,
            "failed"       : failed,
            "missed"       : missed,
            'success_rate' : success_rate,
            'failed_rate'  : failed_rate,
            'missed_rate'  : missed_rate
        }

    def getTrigger(self):
        if not self.trigger:
            defaults = {'timezone':Task.objects.timezone} 
            trigger_args = self.getTriggerArgs()
            if self.type == 'date':
                trigger = DateTrigger(defaults, *trigger_args)
            elif self.type == 'interval':
                trigger = IntervalTrigger(defaults, **trigger_args)
            elif self.type == 'cron':
                trigger = CronTrigger(defaults, **trigger_args)
            self.trigger = trigger
        return self.trigger

    def validate(self):
        return True

    def compute_next_run_time(self, now):
        self.next_run_time = self.getTrigger().get_next_fire_time(now)
        return self.next_run_time

    def __unicode__(self):
        id = 0 if self.id is None else self.id
        return "task<%d %s (%s %s) (%s %s)>" % (id, self.name, self.type, self.run_time, self.run_type, self.run_entry)

    def run(self):
        logging.info('run task manual '+str(self))
        url = self.run_entry
        if self.run_type.lower() == 'post':
            req = urllib2.urlopen(url, self.run_params)
        else:
            if len(self.run_params) > 0:
                seperator = '&' if url.find('?') > 0 else '?'
                url += seperator + self.run_params
            req = urllib2.urlopen(url)

        try:
            resp = req.read()
            Task.objects.job_stats.succ(self.id)
            return resp
        except:
            Task.objects.job_stats.fail(self.id)
            req.close()
            return '执行任务失败'
