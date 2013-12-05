#!/usr/bin/env python
# -*- coding:utf-8 -*-

import logging, os, sys, time, random

from threading import Thread, Event, Lock
from datetime import datetime, timedelta
from dateutil.tz import gettz

from django.conf import settings

from apscheduler.util import *
from apscheduler.job import MaxInstancesReachedError
from apscheduler.events import *
from apscheduler.threadpool import ThreadPool

from mycron.task.jobstore import JobStore, JobStats, JobSync

from redis import StrictRedis


logger = logging.getLogger('cron.backend2')
fhd = logging.FileHandler('/tmp/cron_webdev_com_backend.log')
fhd.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
logger.addHandler(fhd)
logger.setLevel(logging.DEBUG)

class Scheduler(object):
    def __init__(self, **options):
        self._wakeup = Event()
        self._jobstore = None
        self._threadpool = None
        self._jobstats = None
        self._jobsync = None
        self._jobsync_lock = Lock()
        self._jobstats_lock = Lock()
        self._jobstore_lock = Lock()

        self._listeners = []
        self._listeners_lock = Lock()

        self.configure(**options)
        
    def configure(self, **options):
        try:
            redis = StrictRedis(**settings.REDISES['default'])
            redis2 = StrictRedis(**settings.REDISES['default'])
            redis3 = StrictRedis(**settings.REDISES['default'])
        except:
            logging.exception('cannot connect to redis')
            raise

        self._timezone = gettz('Asia/Chongqing')
        self._threadpool = ThreadPool()
        self._jobstore = JobStore(redis, self._timezone) #todo Jobstore
        self._jobstats = JobStats(redis2)
        self._jobsync  = JobSync(redis3)
        self.misfire_grace_time = 1
        self.coalesce = True
        self.daemonic = True
        
    def start(self):
        logger.info('Scheduler is starting...')
        with self._jobstore_lock:
            self._jobstore.load_jobs(datetime.now(self._timezone))
        self._stopped = False

        self._thread = Thread(target=self._main_loop, name="APScheduler")
        self._thread.setDaemon(True)
        logger.info('start main loop thread')
        self._thread.start()
        
        self._sync_thread = Thread(target=self._sync_jobs, name="JobsSync")
        self._sync_thread.setDaemon(True)
        logger.info('start job sync thread')
        self._sync_thread.start()
    
    def shutdown(self, wait=True, shutdown_threadpool=True, close_jobstore=True):
        if not self.running:
            return

        logger.info('Scheduler is stopping')
        self._stopped = True
        self._wakeup.set()

        self._threadpool.shutdown(wait)
        if self._sync_thread:
            self._sync_thread.join()
        if self._thread:
            self._thread.join()

        if close_jobstore:
            self._jobstore.close()
        logger.info('Scheduler is stoped')
        
    @property
    def running(self):
        return not self._stopped and self._thread and self._thread.isAlive()

    def _update_job(self, job, change_type):
        with self._jobstore_lock:
            if change_type == 'add':
                ret = self._jobstore.add_job(job)
            elif change_type == 'remove':
                ret = self._jobstore.remove_job(job)
            elif change_type == 'update':
                ret = self._jobstore.update_job(job)
            else:
                ret = 'invalid change_type %s' % change_type


    def _sync_jobs(self):
        while not self._stopped:
            if self._jobsync.has_notifier():
                while True:
                    now = datetime.now(self._timezone)
                    job_id, change_type, job = self._jobsync.pop(now)
                    if job_id == 0:
                        break
                    logger.debug('pop %d|%s' % (job_id, change_type))
                    self._update_job(job, change_type)
                self._wakeup.set()
            time.sleep(3)
        
    def _main_loop(self):

        logger.info('Scheduler is started')
        self._fire(SchedulerEvent(EVENT_SCHEDULER_START))

        self._wakeup.clear()
        while not self._stopped:
            now = datetime.now(self._timezone)
            next_wakeup_time = self._process_jobs(now)
            if next_wakeup_time is not None:
                wait_seconds = time_difference(next_wakeup_time, now)
                logger.debug('Next wakeup is due at %s (in %f seconds)', next_wakeup_time, wait_seconds)
                self._wakeup.wait(wait_seconds)
                self._wakeup.clear()
            else:
                logger.debug('No jobs; waiting until a job is added')
                self._wakeup.wait()
                self._wakeup.clear()

        logger.info('Scheduler has been shut down')
        self._fire(SchedulerEvent(EVENT_SCHEDULER_SHUTDOWN))

    def _run_job(self, job, run_times):
        for run_time in run_times:
            difference = datetime.now(self._timezone) - run_time
            grace_time = timedelta(seconds=job.misfire_grace_time)
            if difference > grace_time:
                # Notify listeners about a missed run
                event = JobEvent(EVENT_JOB_MISSED, job, run_time)
                self._fire(event)
                with self._jobstats_lock:
                    self._jobstats.miss(job.id)
                logger.warning('Run time of job "%s" was missed by %s', job, difference)
            else:
                try:
                    job.add_instance()
                except MaxInstancesReachedError:
                    event = JobEvent(EVENT_JOB_MISSED, job, run_time)
                    self._fire(event)
                    with self._jobstats_lock:
                        self._jobstats.miss(job.id)
                    logger.warning('Execution of job "%s" skipped: maximum number of running instances reached (%d)',
                                   job, job.max_instances)
                    break

                logger.info('1Running job "%s" (scheduled at %s)', job, run_time)

                try:
                    retval = job.run()
                except:
                    exc, tb = sys.exec_info()[1:]
                    with self._jobstats_lock:
                        self._jobstats.fail(job.id)
                    event = JobEvent(EVENT_JOB_ERROR, job, run_time, exception=exc, traceback=tb)
                    self._fire(event)
                    logger.exception('Job "%s" raised an exception', job)
                else:
                    with self._jobstats_lock:
                        self._jobstats.succ(job.id)
                    event = JobEvent(EVENT_JOB_EXECUTED, job, run_time, retval=retval)
                    self._fire(event)
                    logger.info('Job "%s" executed successfully', job)

                logger.info('2runned job "%s" (scheduled at %s)', job, run_time)
                job.remove_instance()

                if job.coalesce:
                    break

    def _process_jobs(self, now):
        logger.debug('processing jobs')
        next_wakeup_time = None

        with self._jobstore_lock:
            jobs = tuple(self._jobstore.jobs)

        for job in jobs:
            run_times = job.get_run_times(now)
            if run_times:
                self._threadpool.submit(self._run_job, job, run_times)
                if job.compute_next_run_time(now + timedelta(microseconds=1)):
                    with self._jobstore_lock:
                        self._jobstore.update_job(job)
                else:
                    with self._jobstore_lock:
                        self._jobstore.remove_job(job)

            if not next_wakeup_time:
                next_wakeup_time = job.next_run_time
            elif job.next_run_time:
                next_wakeup_time = min(next_wakeup_time, job.next_run_time)

        logger.debug('processing jobs end')
        return next_wakeup_time


    def add_listener(self, callback, mask=EVENT_ALL):
        """
        添加事件监听器
        """
        with self._listeners_lock:
            self._listeners.append((callback, mask))

    def remove_listener(self, callback):
        """
        移除事件监听器
        """
        with self._listeners_lock:
            for i, (cb, _) in enumerate(self._listeners):
                if callback == cb:
                    del self._listeners[i]

    def _fire(self, event):
        """
        事件分发
        """
        with self._listeners_lock:
            listeners = tuple(self._listeners)

        for cb, mask in listeners:
            if event.code & mask:
                try:
                    cb(event)
                except:
                    logger.exception('Error notifying listener')

