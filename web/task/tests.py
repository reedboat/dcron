#coding:utf-8
from datetime import datetime
from dateutil import tz

from django.test import TestCase
from django.conf import settings

from mycron.task.jobstore import JobStore, JobSync, JobStats
from mycron.task.models import Task
from mycron.scheduler import Scheduler

from redis import StrictRedis
from apscheduler.job import Job
from apscheduler.triggers import IntervalTrigger

class TaskTest(TestCase):
    def setUp(self):
        self.redis = StrictRedis(**settings.REDISES['default'])
        self.job_changes_pool_key = 'queue_job_changes'
        self.job_sync = JobSync(self.redis)

    def tearDown(self):
        Task.objects.all().delete()
        #self.redis.delete('active_jobs_pool')
        self.redis.delete(self.job_changes_pool_key)
        self.redis.delete('job_stats.1')

    def testAddJob(self):
        task = self.generateTask()
        task.run_time = '{"days":0, "hours":0, "minutes":10, "seconds":0}'
        task.save()
        self.assertTrue(task.id > 0)

        job = task.getJob()
        now = Task.objects.now()
        self.assertTrue(job.compute_next_run_time(now) is not None)
        self.assertEqual(600, job.trigger.interval_length)
        self.assertEqual(task.run_entry, job.func)

        self.assertEqual(1, self.redis.llen(self.job_changes_pool_key))

    def testGetJob(self):
        task = self.generateTask()
        task.save()
        job = task.getJob()
        self.assertEqual(task.id, job.id)
        self.assertEqual(task.name, job.name)
        self.assertEqual(task.run_entry, job.func)
        self.assertEqual(str(task.getTrigger()), str(job.trigger))

    def testDelete(self):
        task = self.generateTask()
        task.active = 1
        task.save()
        now = Task.objects.now()
        job_id, change_type, job = self.job_sync.pop(now)
        self.assertEqual(task.id, job_id)
        self.assertEqual('add', change_type)

        task_id = task.id
        task.delete()
        job_id, change_type, job = self.job_sync.pop(now)
        self.assertEqual(task_id, job_id)
        self.assertEqual('remove', change_type)

    def testUpdate(self):
        task = self.generateTask()
        task.save()
        now = Task.objects.now()
        job_id, change_type, job = self.job_sync.pop(now)
        task.run_time = '2013-09-10 00:00:00'
        task.type = 'date'
        task.save()
        job_id, change_type, job = self.job_sync.pop(now)
        self.assertEqual(task.id, job_id)
        self.assertEqual('update', change_type)

    def testEnable(self):
        task = self.generateTask()
        task.active = 0
        task.save()
        self.assertEqual(0, self.job_sync.count())
        task.disable()
        self.assertEqual(0, self.job_sync.count())

        task.enable()
        now = Task.objects.now()
        job_id, change_type, job = self.job_sync.pop(now)
        self.assertEqual(task.id, job_id)
        self.assertEqual('add', change_type)

    def generateTask(self):
        task = Task()
        task.name = 'Task1'
        task.run_time = '{"days":0, "hours":0, "minutes":10, "seconds":0}'
        task.run_entry = 'http://baidu.com'
        task.run_method = 'post'
        task.active = 1
        return task

    def testDisable(self):
        task = self.generateTask()
        task.active = 1
        task.save()

        now = Task.objects.now()
        job_id, change_type, job = self.job_sync.pop(now)
        self.assertEqual(task.id, job_id)
        self.assertEqual('add', change_type)

        task.enable()
        self.assertEqual(0, self.job_sync.count())

        task.disable()
        job_id, change_type, job = self.job_sync.pop(now)
        self.assertEqual(task.id, job_id)
        self.assertEqual('remove', change_type)

    def testRun(self):
        task = self.generateTask()
        task.save()
        self.redis.delete('job_stats.%d' % task.id)
        self.assertEqual(0,task.stats['total'])
        task.run()
        self.assertEqual(1,task.stats['total'])


class JobSyncTest(TestCase):
    def setUp(self):
        self.redis = StrictRedis(**settings.REDISES['default'])
        self.sync = JobSync(self.redis)
        self.key  = 'queue_job_changes'

    def tearDown(self):
        self.redis.delete(self.key)

    def test_notifier(self):
        self.assertFalse(self.sync.has_notifier())
        self.redis.lpush(self.key, '1||add||None')
        self.assertTrue(self.sync.has_notifier())

    def test_push(self):
        self.assertFalse(self.sync.has_notifier())
        self.sync.push(1, 'add')
        self.assertTrue(self.sync.has_notifier())

    def test_pop(self):
        self.assertFalse(self.sync.has_notifier())

        timezone = tz.gettz('Asia/Chongqing')
        now = datetime.now(timezone)
        item = self.sync.pop(now)
        self.assertEqual(0, item[0])

        self.sync.push(1, 'add')
        self.assertTrue(self.sync.has_notifier())
        item = self.sync.pop(now)
        self.assertFalse(self.sync.has_notifier())
        self.assertEqual(1, item[0])
        self.assertEqual('add', item[1])

    def test_handle(self):
        pass


class JobStatsTest(TestCase):
    def setUp(self):
        self.redis = StrictRedis(**settings.REDISES['default'])
        self.stats = JobStats(self.redis)

    def tearDown(self):
        self.redis.delete('job_stats.1')

    def testIncr(self):
        job_id = 1
        field = 'success'
        count = self.stats.get(job_id, field)
        self.assertEqual(0, count)

        self.stats.incr(job_id, field, 1)
        count = self.stats.get(job_id, field)
        self.assertEqual(1, count)

        self.stats.incr(job_id, field, 2)
        count = self.stats.get(job_id, field)
        self.assertEqual(3, count)

        self.stats.incr(job_id, 'failed')
        self.stats.get(job_id, field)
        self.assertEqual(3, count)

    def testGet(self):
        job_id = 1
        self.stats.incr(job_id, 'failed', 1)
        self.stats.incr(job_id, 'success', 2)
        counts = self.stats.get(job_id)
        self.assertEqual(1, counts['failed'])
        self.assertEqual(2, counts['success'])


class JobStoreTest(TestCase):
    def setUp(self):
        self.redis = StrictRedis(**settings.REDISES['default'])
        self.store = JobStore(self.redis, 'Asia/Chongqing')
        self.store.clear()
        self.redis.delete('active_jobs_pool')
        self.init()

    def tearDown(self):
        self.redis.delete('active_jobs_pool')
        self.store.clear()

    def init(self):
        tz = self.store.timezone
        trigger = IntervalTrigger({}, minutes=5, timezone=tz)
        url     = 'http://t.cn'
        now = datetime.now(tz)

        self.job1 = Job(1, trigger, url)
        self.job1.compute_next_run_time(now)
        self.job2 = Job(2, trigger, url)
        self.job2.compute_next_run_time(now)

        self.store.add_job(self.job1)
        self.store.add_job(self.job2)


        self.now = now
        self.url = url
        self.trigger = trigger

    def testLoadJob(self):
        Task.objects.all().delete()
        task = self.createTask()
        task.save()
        job = self.store.load_job(task.id, self.now)
        self.assertEqual(self.url, job.func)

    def testLoadJobs(self):
        Task.objects.all().delete()
        self.store.clear()

        for i in range(3):
            task = self.createTask()
            task.save()
            self.redis.sadd('active_jobs_pool', task.id)

        self.assertEqual(3, self.store.count())
        self.assertEqual(0, len(self.store.jobs))
        self.store.load_jobs()
        self.assertEqual(3, len(self.store.jobs))


    def testAddJob(self):
        self.assertEqual(2, self.store.count())
        job = Job(3, self.trigger, self.url)
        job.compute_next_run_time(self.now)
        self.store.add_job(job)
        self.assertEqual(3, self.store.count())

    def testRemoveJob(self):
        self.assertEqual(2, self.store.count())
        self.store.remove_job(id=1)
        self.assertEqual(1, self.store.count())
        self.store.remove_job(id=3)
        self.assertEqual(1, self.store.count())

    def createTask(self):
        import json
        task = Task()
        task.run_time = json.dumps({'minutes':10})
        task.name = 'name'
        task.run_entry = self.url
        return task

    def testUpdateJob(self):
        task = self.createTask()
        task.name = 'name1'
        task.save()
        self.store.clear()
        self.redis.sadd(self.store.active_jobs_key, task.id)
        self.store.load_jobs()
        job = self.store.find_job(task.id)
        self.assertEqual(task.name, job.name)

        task.name = 'name2'
        task.save()
        self.store.update_job(id=task.id)
        job = self.store.find_job(task.id)
        self.assertEqual(task.name, job.name)



    def testFindJob(self):
        self.assertEqual(2, self.store.count())
        job = self.store.find_job(1)
        self.assertEqual(1, job.id)
        self.assertIsNone(self.store.find_job(3))

    def testHasJob(self):
        self.assertTrue(self.store.has_job(1))
        self.assertFalse(self.store.has_job(3))

class SchedulerTest(TestCase):
    def setUp(self):
        self.scheduler = Scheduler()
        self.tz = tz.gettz('Asia/Chongqing')

    def tearDown(self):
        self.scheduler = None

    def testRunJob(self):
        trigger = IntervalTrigger({}, minutes=5, timezone=self.tz)
        url     = 'http://t.cn'
        job = Job(3, trigger, url)
        run_times = []
        self.scheduler._run_job(job, run_times)

    def testUpdateJob(self):
        trigger = IntervalTrigger({}, minutes=5, timezone=self.tz)
        url     = 'http://t.cn'
        job = Job(3, trigger, url)
        change_type = 'add'
        self.scheduler._update_job(job, change_type)

