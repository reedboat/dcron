#!/usr/bin/env python
# -*- coding:utf-8 -*-
# vim set expandtab
import logging, sys, time
from threading import Lock

from django.core.management.base import BaseCommand 
from django.conf import settings

from apscheduler.events import (EVENT_JOB_EXECUTED, SchedulerEvent, EVENT_SCHEDULER_START,
                                EVENT_SCHEDULER_SHUTDOWN, EVENT_JOB_ERROR, EVENT_JOB_MISSED)

from mycron.scheduler import Scheduler

class Command(BaseCommand):
    def job_success(self, event):
        logger = logging.getLogger(__name__)
        logger.info("job_success:" + str(event.job) + " run_time:" + str(event.scheduled_run_time))
        logger.debug("job_success:" + str(event.job) + " run_time:" + str(event.scheduled_run_time) + " result:" + event.retval)

    def job_failed(self, event):
        logger = logging.getLogger(__name__)
        logger.error("job_failed:" + str(event.job) + " run_time:" + str(event.scheduled_run_time) + " exception:" + str(event.exception))
        logger.debug("job_failed:" + str(event.job) + " run_time:" + str(event.scheduled_run_time) + " exception:" + str(event.exception) + str(event.traceback))

    def job_missed(self, event):
        logger = logging.getLogger(__name__)
        logger.error("job_missed:" + str(event.job) + " run_time:" + str(event.scheduled_run_time))

    def handle(self, *args, **options):
        #logger = logging.getLogger('cron.backend')
        logger = logging.getLogger(__name__)
        fhd = logging.FileHandler('/tmp/cron_webdev_com_backend.log')
        fhd.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
        logger.addHandler(fhd)
        logger.setLevel(logging.DEBUG)

        print "scheduler is preparing..."
        scheduler = Scheduler(standalone=False, timezone='Asia/Chongqing')

        scheduler.add_listener(self.job_success, EVENT_JOB_EXECUTED)
        scheduler.add_listener(self.job_failed, EVENT_JOB_ERROR)
        scheduler.add_listener(self.job_missed, EVENT_JOB_MISSED)
        print "scheduler is prepared"

        try:
            print "scheduler is starting..."
            logger.info('scheduler is starting...')
            scheduler.start()
            print "scheduler started"
            logger.info('scheduler is started...')
            while True:
                time.sleep(100)
        except (KeyboardInterrupt, SystemExit):
            scheduler.shutdown()
            logger.info("shutdown by Ctrl^C or exit signal")
        except Exception as e:
            logger.error(e)
            pass

