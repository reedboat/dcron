#!/usr/bin/env python
# -*- coding:utf-8 -*-
# vim set expandtab

from apscheduler.job import Job
from apscheduler.jobstores.sqlalchemy_store import SQLAlchemyJobStore
from dateutil.tz import gettz
from datetime import datetime, timedelta
from apscheduler.triggers import IntervalTrigger
from apscheduler.scripts import HttpScript


if __name__ == '__main__':


    script = HttpScript(url='http://baidu.com')
    local_tz = gettz('Asia/Chongqing')
    defaults = {'timezone': local_tz}
    trigger = IntervalTrigger(defaults, seconds=3)

    #Base.metadata.create_all(engine)
    store = SQLAlchemyJobStore(url='sqlite:////tmp/task.db', tablename='tasks')
    job   = store.get_job(3)
    #if not job:
    #    job = Job(id=3, name='BaiduCheck', script=script, trigger=trigger)
    #    store.add_job(job)

    print job
    if job:
        print job.run()
        now = datetime.now(local_tz)
        print job.compute_next_run_time(now)
        print job.get_run_times(now+timedelta(seconds=60))
