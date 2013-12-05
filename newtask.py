#!/usr/bin/env python
# -*- coding:utf-8 -*-
# vim set expandtab

import cPickle

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, create_engine
from sqlalchemy.orm import sessionmaker

from apscheduler.job import Job

Base = declarative_base()

class Task(Base):
    __tablename__ = 'tasks'

    id = Column(Integer, primary_key=True)
    name = Column(String)
    script = Column(String)
    trigger = Column(String)
    def __init__(self, id, name, script, trigger):
        self.name = name
        self.script = script
        self.trigger = trigger

    def __repr__(self):
        return "<Task(id=%d, name='%s', script='%s', trigger='%s'>" % (
                self.id, self.name, self.script, self.trigger
        )
    
    def create_job(self):
        return Job(id=self.id, name=self.name, script=cPickle.loads(str(self.script)),
                    trigger=cPickle.loads(str(self.trigger)))




if __name__ == '__main__':
    from dateutil.tz import gettz
    from datetime import datetime, timedelta
    from apscheduler.triggers import IntervalTrigger
    from apscheduler.scripts import HttpScript

    store = SQLAlchemyJobStore(url='sqlite:////tmp/task.db', tablename='tasks')
    Session = sessionmaker(bind=engine)
    session = Session()

    script = HttpScript(url='http://baidu.com')
    local_tz = gettz('Asia/Chongqing')
    defaults = {'timezone': local_tz}
    trigger = IntervalTrigger(defaults, seconds=3)

    #Base.metadata.create_all(engine)
    row = session.query(Task).get(3)
    if not row:
        row = Task(name='BaiduCheck', script=cPickle.dumps(script), trigger=cPickle.dumps(trigger))
        session.add(row)
        session.commit()

    job = row.create_job()
    print job.run()
    now = datetime.now(local_tz)
    print job.compute_next_run_time(now)
    print job.get_run_times(now+timedelta(seconds=60))
