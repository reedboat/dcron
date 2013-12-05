import logging, pickle
from datetime import datetime
from dateutil import tz

from apscheduler.job import Job


class JobSync(object):
    def __init__(self, redis):
        self.redis = redis
        self.key   = 'queue_job_changes'

    def has_notifier(self):
        return self.redis.llen(self.key) > 0

    def pop(self, now):
        item = self.redis.rpop(self.key)
        if item is None:
            return 0, '', None
        try:
            job_id, change_type, job_str = item.split('||')
            job_id = int(job_id)
            if job_str == 'None':
                job = None
            else:
                job_state = pickle.loads(job_str)
                job = Job.__new__(Job)
                job.__setstate__(job_state)
                job.compute_next_run_time(now)
            return job_id, change_type, job
        except:
            logger=logging.getLogger('cron.backend')
            logger.exception('sync item invalid')
            return 0, ''

    def push(self, job_id, change_type, job=None):
        if job:
            job_state = job.__getstate__()
            job_str = pickle.dumps(job_state, pickle.HIGHEST_PROTOCOL)
        else:
            job_str = 'None'

        item = '%d||%s||%s' % (job_id, change_type, job_str)
        self.redis.lpush(self.key, item)

    def count(self):
        return self.redis.llen(self.key)

class JobStats(object):
    def __init__(self, redis, key_prefix='job_stats.'):
        self.redis = redis
        self.job_stats_prefix = key_prefix

    def incr(self, job_id, field, count=1):
        key = self.job_stats_prefix + str(job_id)
        self.redis.hincrby(key, field ,count)

    def succ(self, job_id):
        field = 'success'
        self.incr(job_id, field)

    def fail(self, job_id):
        field = 'failed'
        self.incr(job_id, field)

    def miss(self, job_id):
        field = 'missed'
        self.incr(job_id, field)

    def get(self, job_id, field=None):
        key = self.job_stats_prefix + str(job_id)
        if field is None:
            ret = self.redis.hgetall(key)
            for k,v in ret.items():
                ret[k] = int(v)
            return ret
        else:
            ret = self.redis.hget(key, field)
            return int(ret) if ret else 0
    
class JobStore(object):
    jobs = []
    active_jobs_key = ''
    redis = None

    def __init__(self, redis, timezone):
        self.redis = redis
        self.active_jobs_key = 'active_jobs_pool'
        if isinstance(timezone, tz.tzfile):
            self.timezone = timezone
        else:
            self.timezone = tz.gettz(timezone)

    def load_job(self, job_id, now=None):
        from mycron.task.models import Task
        if now is None:
            now = datetime.now(self.timezone)
        try:
            task = Task.objects.get(pk=job_id)
            job = task.getJob()
            job.compute_next_run_time(now)
        except:
            logger=logging.getLogger('cron.backend')
            logger.exception('cannot load job(id=%d)' % job_id)
            logger.debug('task conns %d' % Task.objects.count())
            return None
        else:
            return job

    def load_jobs(self, now=None):
        jobs = []
        if now is None:
            now = datetime.now(self.timezone)
        job_ids = self.redis.smembers(self.active_jobs_key)
        for job_id in job_ids:
            job = self.load_job(int(job_id), now)
            if job and job.next_run_time:
                jobs.append(job)
        self.jobs = jobs

    def add_job(self, job=None, id=0):
        if id > 0:
            job = self.load_job(id)

        if job and isinstance(job, Job):
            self.remove_job(id=job.id)
            if job.next_run_time:
                self.redis.sadd(self.active_jobs_key, job.id)
                self.jobs.append(job)
                return True
        else:
            return False

    def remove_job(self, job=None, id=0):
        if job and isinstance(job, Job):
            id = job.id
        if id > 0:
            job = self.find_job(id)

        if job and isinstance(job, Job):
            self.redis.srem(self.active_jobs_key, job.id)
            self.jobs.remove(job)
            return True
        else:
            return False

    def update_job(self, job=None, id=0):
        if id > 0:
            job = self.load_job(id)

        if job and isinstance(job, Job):
            if job.next_run_time is None:
                return self.remove_job(id=job.id)
            else:
                return self.add_job(job)
        else:
            return False

    def find_job(self, id):
        jobs = [job for job in self.jobs if job.id == id]
        if len(jobs) > 0:
            return jobs[0]
        return None

    def has_job(self, id):
        return self.redis.sismember(self.active_jobs_key, id)

    def count(self):
        return self.redis.scard(self.active_jobs_key)

    def close(self):
        pass

    def clear(self):
        self.jobs = []
        self.redis.delete(self.active_jobs_key)
