import pickle
import traceback

try:
    from sqlalchemy import create_engine, Table, Column, MetaData
    from sqlalchemy import Integer, DateTime, Unicode
except ImportError:  # pragma: nocover
    raise ImportError('JobReporter requires SQLAlchemy installed')

class JobReporter(object):
    def __init__(self, url=None, engine=None, tablename='job_stats', metadata=None,
                 pickle_protocol=pickle.HIGHEST_PROTOCOL):
        self.pickle_protocol = pickle_protocol

        if engine:
            self.engine = engine
        elif url:
            self.engine = create_engine(url)
        else:
            raise ValueError('Need either "engine" or "url" defined')

        self.statistics_t = Table(
            tablename, metadata or MetaData(),
            Column('job_id', Integer, primary_key=True),
            Column('runs', Integer, nullable=False),
            Column('failed', Integer, nullable=False),
            Column('missed', Integer, nullable=False),
            Column('succed', Integer, nullable=False),
            Column('last_run_time', DateTime),
            Column('next_run_time', DateTime),
            Column('status', Unicode(64), nullable=False, default=u''),
            Column('cost', Integer, nullable=False, default=0)
        )
        self.statistics_t.create(self.engine, True)
        
    def get(self, job_id):
        select = self.statistics_t.select().where(self.statistics_t.c.job_id == job_id)
        row = self.engine.execute(select).fetchone()
        if row:
            print row
            return dict(row)
        else:
            return {
                "job_id": job_id,
                'runs'  : 0,
                "succed": 0,
                "failed": 0,
                'missed': 0,
                'last_run_time': None,
                'next_run_time': None,
                'cost': 0,
                'is_new_record': True, 
            }

    def report(self, job_id, status, run_time, next_run_time, cost=0):
        running_dict = self.get(job_id)
        if running_dict is None:
            return False

        print running_dict
        is_new_record = False
        if running_dict.has_key('is_new_record'):
            del running_dict['is_new_record'] 
            is_new_record = True

        # status and count
        running_dict['status'] = unicode(status)

        if status == 'running':
            running_dict['runs'] += 1
            running_dict['last_run_time'] = run_time
            running_dict['next_run_time'] = next_run_time
        elif status == 'missed':
            running_dict[status] += 1
            running_dict['next_run_time'] = next_run_time
        else:
            running_dict[status] += 1
            running_dict['last_cost'] = cost

        print running_dict

        try:
            if is_new_record:
                sql = self.statistics_t.insert().values(**running_dict)
                result = self.engine.execute(sql)
            else:
                sql = self.statistics_t.update().where(self.statistics_t.c.job_id == job_id).\
                    values(**running_dict)
                result = self.engine.execute(sql)
        except:
            traceback.print_exc()
            return False

        if result:
            return True

        return False
