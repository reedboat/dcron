#!/usr/bin/env python
# -*- coding:utf-8 -*-
# vim set expandtab

from dateutil.tz import gettz
from datetime import datetime, timedelta
from apscheduler.reporter import JobReporter


if __name__ == '__main__':

    local_tz = gettz('Asia/Chongqing')
    defaults = {'timezone': local_tz}

    stat = JobReporter(url='sqlite:////tmp/task.db', tablename='job_stats')
    job_id = 1
    status = 'missed'
    run_time = datetime.now()
    next_run_time = run_time + timedelta(seconds=3600)
    stat.report(job_id, 'missed', run_time, next_run_time, 0)

