from datetime import timedelta

from apscheduler.triggers import Trigger
from apscheduler.scripts import Script
from apscheduler.util import datetime_repr

class Job(object):
    coalesce = True
    misfire_grace_time = 30
    def __init__(self, trigger, script, id=None, name=None, coalesce=True, misfire_grace_time=30):
        if not isinstance(script, Script):
            raise ValueError("job's script is not valid a Script instance")
        if not isinstance(trigger, Trigger):
            raise ValueError("job's trigger is not valid a Trigger instance")

        self.id   = id
        self.name = name
        self.script = script
        self.trigger = trigger
        self.next_run_time = None
        #self.coalesce = coalesce
        self.misfire_grace_time = misfire_grace_time
        self._lock = Lock()

    def run(self):
        return self.script.run()

    def compute_next_run_time(self, now):
        try:
            next_run_time = self.trigger.get_next_fire_time(now)
            if next_run_time != self.next_run_time:
                self.next_run_time = next_run_time
        except:
            logger.exception("get next fire time of job(id=%d, name=%s) from time %s" % (self.id, self.name, now))
            self.next_run_time = None
        return self.next_run_time
    
    def get_run_times(self, now):
        run_times = []
        run_time = self.next_run_time
        increment = timedelta(microseconds=1)
        while run_time and run_time <= now:
            run_times.append(run_time)
            try:
                run_time = self.trigger.get_next_fire_time(run_time + increment)
            except:
                logger.exception("get next fire time of job(id=%d, name=%s) from time %s" % (self.id, self.name, run_time+increment))
                run_time = None
        
        return run_times

    def __getstate__(self):
        state = self.__dict__.copy()
        state.pop('_lock', None)
        return state

    def __setstate__(self, state):
        state['_lock'] = Lock()
        for k,v in state.items():
            self.__dict__[str(k)] = v
        self.__dict__ = state
        if self.__dict__.has_key('next_run_time'):
            self.__dict__['next_run_time'] = None

    def __repr__(self):
        return "<Job(id=%d, name='%s', script='%s', trigger='%s'>" % (
                self.id, self.name, self.script, self.trigger
        )

    def __str__(self):
        return '<Job(%d:%s, trigger: %s, next run at: %s)>' % (self.id, self.name, self.trigger, datetime_repr(self.next_run_time))

    def __eq__(self, other):
        if isinstance(other, Job):
            return self.id is not None and other.id == self.id or self is other
        return NotImplemented

