#!/usr/bin/env python
# -*- coding:utf-8 -*-
# vim set expandtab

from dateutil.tz import gettz
from datetime import datetime, timedelta

from hotqueue import HotQueue

from apscheduler.job import Job
from apscheduler.jobstores.sqlalchemy_store import SQLAlchemyJobStore
from apscheduler.triggers import IntervalTrigger
from apscheduler.scripts import HttpScript


if __name__ == '__main__':

    script = HttpScript(url='http://baidu.com')
    local_tz = gettz('Asia/Chongqing')
    defaults = {'timezone': local_tz}
    trigger = IntervalTrigger(defaults, seconds=3)

    store = SQLAlchemyJobStore(url='sqlite:////tmp/task.db', tablename='tasks')
    job   = store.get_job(3)
    if not job:
        job = Job(id=3, name='BaiduCheck', script=script, trigger=trigger)
        store.add_job(job)

    print job

    job.trigger = IntervalTrigger(defaults, seconds=5)
    store.update_job(job)

    queue = HotQueue('job_changes')
    queue.put({'job_id':job.id, 'opt_type':'update'})


