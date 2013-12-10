from dateutil.tz import gettz

from apscheduler.job import Job
from apscheduler.triggers import IntervalTrigger
from apscheduler.scripts import HttpScript

t = IntervalTrigger({}, minutes=5, timezone=gettz('Asia/Chongqing'))
s = HttpScript(url='http://baidu.com')

job = Job(t, s)
print job.__getstate__()
