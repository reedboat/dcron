#!/usr/bin/env python
# -*- coding:utf-8 -*-
# vim set expandtab

import logging
from threading import Thread, Event, Lock
from dateutil.tz import gettz
from datetime import datetime, timedelta

from apscheduler.util import time_difference
from apscheduler.threadpool import ThreadPool
from apscheduler.job import Job

class Store(object):
    pass


class LocalScheduler(object):

    #初始化worker线程，reporter线程，updater线程
    def __init__(self, **options):
        self._wakeup = Event()
        self._jobstore = None
        self._jobs     = {}
        self._logger   = None
        self._log_queue = None

        self._jobs_lock = Lock()
        self._log_queue_lock = Lock()


        self._worker_threadpool = None
        self._reporter_thread   = None
        self._main_thread       = None
        self._updater_thread    = None
        self._monitor_thread    = None

        self.configure(**options)

    def configure(self, **options):
        self._timezone = gettz('Asia/Chongqing')
        #self._jobstore = 

        self._worker_threadpool = ThreadPool()
        self._main_thread       = Thread(target = self._main_loop, name = 'main')
        #self._updater_thread    = Thread(target = self._update_loop, name = 'updater')
        #self._reporter_thread   = Thread(target = self._reporte_loop, name = 'reporter')
        #self._monitor_thread    = Thread(target = self._update_loop, name = 'monitor')
        self._main_thread.setDaemon(True)
        #self._updater_thread.setDaemon(True)
        #self._reporter_thread.setDaemon(True)
        #self._monitor_thread.setDaemon(True)

        self.misfire_grace_time = 1
        self.coalesce = True
        self.daemonic = True

        # configure logger
        self.logger = logging.getLogger('dcron')
        fhd = logging.FileHandler('/tmp/crond.log')
        fhd.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
        self.logger.addHandler(fhd)
        self.logger.setLevel(logging.DEBUG)


    def start(self):
        with self._jobs_lock:
            self.load_jobs()
        self._stopped = False
        #self._main_thread.start()
        self._main_loop()
        print 'main thread is startted'
        #self._updater_thread.start()

    def shutdown(self, shutdown_threadpool=True, close_jobstore=True):
        if not self.running:
            return 
        self.stopped = True
        self._wakeup.set()

        if shutdown_threadpool:
            self._worker_threadpool.shutdown()

        if self._main_thread:
            self._main_thread.join()

        if close_jobstore:
            self._job_store.close()

    def running(self):
        return not self._stopped and self._main_thread and self._main_thread.isAlive()
    

    def now(self):
        return datetime.now(self._timezone)

    def set_jobs(self, jobs):
        now = self.now()
        with self._jobs_lock:
            for job in jobs:
                job.compute_next_run_time(now)
                self._jobs[job.id] = job


    # 加载Job池
    def load_jobs(self):
        #jobs = self._job_store.load_jobs()
        #for job in jobs:
        #    self._jobs[job.id] = job
        pass

    def _main_loop(self):
        print "get into the main loop"
        self._wakeup.clear()
        while not self._stopped:
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

        with self._jobs_lock:
            for job in self._jobs.values():
                run_time_list = job.get_run_times(now)

                if run_time_list:
                    self._worker_threadpool.submit(self._run_job, job, run_time_list)
                    if job.compute_next_run_time(now + timedelta(microseconds=1)):
                        #self._jobs.update(job.id, job)
                        pass
                    else:
                        self._jobs.pop(job.id)

                print 'job.next_run_time:', job.id,  job.next_run_time
                if not next_wakeup_time:
                    next_wakeup_time = job.next_run_time
                elif job.next_run_time:
                    next_wakeup_time = min(next_wakeup_time, job.next_run_time)

        return next_wakeup_time


    def _run_job(self, job, run_time_list):
        print 'run job'
        for run_time in run_time_list:
            now = self.now()
            difference = now - run_time
            grace_time = timedelta(seconds=job.misfire_grace_time)
            if difference > grace_time:
                self.logger.warning('Run time of job "%s" was missed by %s', job, difference)
                #self._log_queue.enqueue([now, job.id, 'missed', job.next_run_time])
            else:
                try:
                    result = job.run()
                    print result
                    #self._log_queue.enqueue([now, job.id, 'run', job.next_run_time])
                except:
                    self.logger.exception('Job "%s" raised an exception', job)
                    #self._log_queue.enqueue([now, job.id, 'failed', job.next_run_time])

            #if job.coalesce:
            #    break



def dummyfunc():
    print 'dummy'
    pass

if __name__ == '__main__':

    from apscheduler.triggers import DateTrigger, IntervalTrigger
    from apscheduler.scripts import HttpScript
    from dateutil.tz import tzoffset

    print callable(dummyfunc)
    lock_type = type(Lock())
    #local_tz = tzoffset('DUMMYTZ', 3600)
    local_tz = gettz('Asia/Chongqing')
    defaults = {'timezone': local_tz}
    RUNTIME = datetime(2013, 12, 5, 7, 40, 0, tzinfo=local_tz)
    trigger1 = IntervalTrigger(defaults, seconds=3)
    trigger2 = DateTrigger(defaults, run_date=RUNTIME)
    script = HttpScript(url='http://baidu.com')
    job1 = Job(1, 'xxx', trigger=trigger1, script=script)
    job2 = Job(2, 'yyy', trigger=trigger2, script=script)

    cron = LocalScheduler()
    cron.set_jobs([job1, job2])
    try:
        cron.start()
    except (KeyboardInterrupt, SystemExit):
        cron.shutdown()
        print "shutdown by Ctrl^C or exit signal"
    except Exception as e:
        print e
