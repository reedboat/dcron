#!/usr/bin/env python
# -*- coding:utf-8 -*-
# vim set expandtab

import sys

from dateutil.tz import gettz
from datetime import datetime, timedelta
from apscheduler.reporter import JobReporter


if __name__ == '__main__':

    local_tz = gettz('Asia/Chongqing')
    defaults = {'timezone': local_tz}

    stat = JobReporter(url='sqlite:////tmp/task.db', tablename='job_stats')
    job_id = 1
    status = 'missed'
    base_time = datetime.now()
    time = base_time
    next_run_time = time + timedelta(seconds=3600)
    stat.report(job_id, 'missed', time, next_run_time, 0)

#    sys.exit()

    time =  time + timedelta(seconds=60)
    next_run_time = time + timedelta(seconds=3600)
    stat.report(job_id, 'running', time, next_run_time, 0)
    time =  time + timedelta(seconds=30)
    stat.report(job_id, 'failed', time, next_run_time, 30)

    time =  time + timedelta(seconds=60)
    next_run_time = time + timedelta(seconds=3600)
    stat.report(job_id, 'running', time, next_run_time, 0)
    time =  time + timedelta(seconds=10)
    stat.report(job_id, 'succed', time, next_run_time, 10)

