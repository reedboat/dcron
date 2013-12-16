#!/usr/bin/env python
# -*- coding:utf-8 -*-
# vim set expandtab

from hotqueue import HotQueue

from apscheduler.job import Job
from apscheduler.jobstores.sqlalchemy_store import SQLAlchemyJobStore
from dateutil.tz import gettz
from datetime import datetime, timedelta
from apscheduler.triggers import IntervalTrigger, DateTrigger
from apscheduler.scripts import HttpScript, CommandScript


if __name__ == '__main__':

    queue = HotQueue('job_changes')
    script = HttpScript(url='http://baidu.comm')
    store = SQLAlchemyJobStore(url='sqlite:////tmp/task.db', tablename='tasks')
    #script = CommandScript(command='ping -c 3 www.baidu.com')
    local_tz = gettz('Asia/Chongqing')
    defaults = {'timezone': local_tz}
    trigger = IntervalTrigger(defaults, seconds=60)
    #trigger = DateTrigger(defaults, run_date=datetime(2013,12,11, 8, 11))

    job = Job(name=u'BaiduCurlWithWrongUrl', script=script, trigger=trigger)

    #print job.run()
    now = datetime.now(local_tz)
    next_run_time = job.compute_next_run_time(now)
    print job.get_run_times(now+timedelta(seconds=60))
    
    if next_run_time:
        print "add job"
        print job
        store.add_job(job)
        queue.put({'opt_type':'add', 'job_id':job.id})
