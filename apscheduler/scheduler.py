#!/usr/bin/env python
# -*- coding:utf-8 -*-
# vim set expandtab


import logging, sys, os, signal, traceback
sys.path.append('..')

from threading import Thread, Event, Lock
from dateutil.tz import gettz, tzlocal
from datetime import datetime, timedelta

from hotqueue import HotQueue

from apscheduler.util import time_difference, asbool, combine_opts
from apscheduler.threadpool import ThreadPool
from apscheduler.job import Job
from apscheduler.jobstores.sqlalchemy_store import SQLAlchemyJobStore

logger = logging.getLogger(__name__)

class SchedulerAlreadyRunningError(Exception):
    """
    Raised when attempting to start or configure the scheduler when it's already running.
    """

    def __str__(self):
        return 'Scheduler is already running'


class LocalScheduler(object):

    _stopped = False
    _main_thread = None

    #init worker thread pool，reporter thread，updater thread
    def __init__(self, gconfig={}, **options):
        self._wakeup = Event()
        self._jobstore = None
        self._jobs     = {}
        self.logger   = None
        self._log_queue = None
        self._change_queue = None

        self._jobs_locks   = {}
        self._jobs_lock = Lock()
        self._log_queue_lock = Lock()


        self._worker_threadpool = None
        self._reporter_thread   = None
        self._main_thread       = None
        self._updater_thread    = None
        self._monitor_thread    = None

        self.configure(gconfig, **options)

    def configure(self, gconfig={}, **options):
        if self.running:
            raise SchedulerAlreadyRunningError

        config = combine_opts(gconfig, 'main.', options)
        self._config = config

        self.misfire_grace_time = int(config.pop('misfire_grace_time', 1))
        self.coalesce = asbool(config.pop('coalesce', True))
        self.daemonic = asbool(config.pop('daemonic', True))
        self.standalone = asbool(config.pop('standalone', False))

        timezone = config.pop('timezone', None)
        self.timezone = gettz(timezone) if isinstance(timezone, basestring) else timezone or tzlocal()

        # config threadpool
        threadpool_opts = combine_opts(config, 'threadpool.')
        self._worker_threadpool = ThreadPool(**threadpool_opts)

        # config jobstore
        jobstore_opts = combine_opts(config, 'jobstore.')
        self._job_store = SQLAlchemyJobStore(**jobstore_opts)

        # config syncqueue
        syncqueue_opts = combine_opts(config, 'syncqueue.')
        self._change_queue = HotQueue(**syncqueue_opts)

        # configure logger
        self.logger = logging.getLogger('dcron')
        fhd = logging.FileHandler('/tmp/crond.log')
        fhd.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
        self.logger.addHandler(fhd)
        self.logger.setLevel(logging.DEBUG)



    def start(self):
        if self.running:
            raise SchedulerAlreadyRunningError

        self.load_jobs()

        self._stopped = False

        if self.standalone:
            self._main_loop()
        else:
            self._main_thread = Thread(target = self._main_loop, name = 'main')
            self._main_thread.setDaemon(self.daemonic)
            self._main_thread.start()
            print 'main thread is startted'

            self._updater_thread = Thread(target = self._sync_changes, name = 'update')
            self._updater_thread.setDaemon(self.daemonic)
            self._updater_thread.start()
            print 'update thread is started'

    def shutdown(self, shutdown_threadpool=True, close_jobstore=True):
        if not self.running:
            return 
        self._stopped = True
        self._wakeup.set()

        if shutdown_threadpool:
            self._worker_threadpool.shutdown()

        if self._main_thread:
            self._main_thread.join()

        if close_jobstore:
            self._job_store.close()

    @property
    def running(self):
        return not self._stopped and self._main_thread and self._main_thread.isAlive()
    

    def now(self):
        return datetime.now(self.timezone)

    def set_jobs(self, jobs):
        now = self.now()
        with self._jobs_lock:
            for job in jobs:
                job.compute_next_run_time(now)
                self._jobs[job.id] = job
                self._jobs_locks[job.id] = Lock()

    # loads jobs pool from db
    def load_jobs(self):
        jobs = self._job_store.load_jobs()
        now = self.now()
        with self._jobs_lock:
            for job in jobs:
                self._add_job(job)

    def _add_job(self, job):
        try:
            now = self.now()
            job.compute_next_run_time(now)
            if job.next_run_time:
                self._jobs[job.id] = job
                self._jobs_locks[job.id] = Lock()
        except:
            logger.exception("add job(id=%d, name=%s) failed" % (job.id, job.name))
            return False

        return True

    def _remove_job(self, job_id):
        try:
            with self._jobs_locks[job_id]:
                del self._jobs[job_id]
            del self._jobs_locks[job_id]
        except:
            logger.exception("remove job(id=%d) failed" % (job_id))
            return False

        return True

    def _main_loop(self):
        print "get into the main loop"
        self._wakeup.clear()
        while not self._stopped:
            print 'check again'
            now = self.now()
            next_wakeup_time = self._process_jobs(now)
            print "next_wakeup_time:", next_wakeup_time
            if next_wakeup_time is not None:
                wait_seconds = time_difference(next_wakeup_time, now)
                self._wakeup.wait(wait_seconds)
                self._wakeup.clear()
            else:
                self._wakeup.wait()
                self._wakeup.clear()
        print "get out the main loop"

    def _process_jobs(self, now):
        next_wakeup_time = None
        print self._jobs

        for job in self._jobs.values():
            run_time_list = job.get_run_times(now)

            if run_time_list:
                self._worker_threadpool.submit(self._run_job, job, run_time_list)

                with self._jobs_locks[job.id]:
                    next_run_time = job.compute_next_run_time(now + timedelta(microseconds=1))

                if not next_run_time:
                    self._remove_job(job.id)

            print 'job.next_run_time:', job.id,  job.next_run_time
            if not next_wakeup_time:
                next_wakeup_time = job.next_run_time
            elif job.next_run_time:
                next_wakeup_time = min(next_wakeup_time, job.next_run_time)

        return next_wakeup_time


    def _run_job(self, job, run_time_list):
        for run_time in run_time_list:
            now = self.now()
            difference = now - run_time
            grace_time = timedelta(seconds=self.misfire_grace_time)
            if difference > grace_time:
                self.logger.warning('Run time of job "%s" was missed by %s', job, difference)
                #self._log_queue.enqueue([now, job.id, 'missed', job.next_run_time])
            else:
                try:
                    # maybe add a timeout handle by join thread. 
                    # t = Thread(job.run); t.start(); t.join(timeout)
                    # refer: http://augustwu.iteye.com/blog/554827
                    result = job.run()
                    print 'job runned success'
                    #self._log_queue.enqueue([now, job.id, 'run', job.next_run_time])
                except:
                    self.logger.exception('Job "%s" raised an exception', job)
                    #self._log_queue.enqueue([now, job.id, 'failed', job.next_run_time])

            if self.coalesce:
                break

    def _sync_changes(self):
        count = 0
        max_items_once = int(self._config.pop('max_items_once', 0))
        while not self._stopped:
            try:
                msg = self._change_queue.get(block=True, timeout=1)
            except:
                logger.exception('get sync item failed')
                msg = None

            if msg:
                opt_type = msg['opt_type']
                job_id   = msg['job_id']
                if job_id > 0 and isinstance(opt_type, basestring):
                    try:
                        self._apply_change(opt_type, job_id)
                    except:
                        pass
                    self.logger.info('apply change "%s" for job(%d)', opt_type, job_id)
                    count += 1

            if not msg or (max_items_once > 0 and count > max_items_once):
                if count > 0:
                    self.logger.info('wakeup main thread by sync thread with %d updates' % count)
                    self._wakeup.set()
                    count = 0


    def _apply_change(self, opt_type, job_id):
            if opt_type == 'add' or opt_type == 'update':
                try:
                    job = self._job_store.get_job(job_id)
                except Exception as e:
                    self.logger.exception(e)

                if job:
                    if opt_type == 'add':
                        if not self._jobs.has_key(job_id):
                            self._add_job(job)
                        else:
                            logger.exception("apply channge '%s job(id=%d, name=%s)' failed" % (opt_type, job.id, job.name))
                    else:
                        #!todo check if compute next_run_time again is necessary
                        now = self.now()
                        job.compute_next_run_time(now)
                        with self._jobs_locks[job_id]:
                            self._jobs[job_id] = job

            elif opt_type == 'delete' or opt_type == 'pause':
                self._remove_job(job_id)
            else:
                self.logger.exception('opt %s job(%d) to jobs pool is not supported' % (opt_type, job_id))


class Watcher:
    """this class solves two problems with multithreaded
    programs in Python, (1) a signal might be delivered
    to any thread (which is just a malfeature) and (2) if
    the thread that gets the signal is waiting, the signal
    is ignored (which is a bug).

    The watcher is a concurrent process (not thread) that
    waits for a signal and the process that contains the
    threads.  See Appendix A of The Little Book of Semaphores.
    http://greenteapress.com/semaphores/

    I have only tested this on Linux.  I would expect it to
    work on the Macintosh and not work on Windows.
    """

    def __init__(self):
        """ Creates a child thread, which returns.  The parent
            thread waits for a KeyboardInterrupt and then kills
            the child thread.
        """
        self.child = os.fork()
        if self.child == 0:
            return
        else:
            self.watch()

    def watch(self):
        try:
            os.wait()
        except KeyboardInterrupt:
            # I put the capital B in KeyBoardInterrupt so I can
            # tell when the Watcher gets the SIGINT
            print 'KeyBoardInterrupt'
            self.kill()
        sys.exit()

    def kill(self):
        try:
            os.kill(self.child, signal.SIGKILL)
        except OSError: pass


            

if __name__ == '__main__':

    config = {
        'timezone': 'Asia/Chongqing',
        'standalone': False,
        'daemonic': False,

        'jobstore.url' : 'sqlite:////tmp/task.db',
        'jobstore.tablename': 'tasks',

        'syncqueue.name': 'job_changes',
    }
    Watcher()
    dcron = LocalScheduler(**config)
    dcron.start()
