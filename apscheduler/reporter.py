import traceback

class JobReporter(object):
    def __init__(self, url=None, engine=None, tablename='job_report', metadata=None,
                 pickle_protocol=pickle.HIGHEST_PROTOCOL):
        self.pickle_protocol = pickle_protocol

        if engine:
            self.engine = engine
        elif url:
            self.engine = create_engine(url)
        else:
            raise ValueError('Need either "engine" or "url" defined')

        self.records_t = Table(
            tablename, metadata or MetaData(),
            Column('job_id', Integer, primary_key=True),
            Column('runs', Integer, nullable=False),
            Column('failed', Integer, nullable=False),
            Column('missed', Integer, nullable=False),
            Column('succed', Integer, nullable=False),
            Column('last_run_time', Datetime, nullable=False),
            Column('next_run_time', Datetime),
            Column('cost', Integer, nullable=False, default=0)
        )
        self.records_t.create(self.engine, True)
        
    def get(self, job_id):
        select = self.records_t.select().where(self.records_t.c.job_id == job_id)
        row = select.engine.execute(select).fetchone()
        if row:
            return dict(row.items)
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

    def report(self, job_id, status, run_time, next_run_time, type, cost):
        running_dict = self.get(job_id)
        if running_dict is None:
            return False

        is_new_record = False
        if running_dict.has_key('is_new_record'):
            del running_dict['is_new_record'] 
            is_new_record = True

        running_dict['runs'] += 1
        running_dict['status'] = status

        if status == 'running':
            running_dict['last_run_time'] = run_time
            running_dict['next_run_time'] = next_run_time
        elif status == 'missed':
            running_dict[status] += 1
            running_dict['next_run_time'] = next_run_time
        else:
            running_dict[status] += 1

        try:
            if is_new_record:
                sql = self.records_t.insert().values(**running_dict)
                result = self.engine.execute(sql)
            else:
                sql = self.records_t.update().where(self.records_t.c.job_id=job_id).values(**running_dict)
                result = self.engine.execute(sql)
        except:
            traceback.print_exc()
            return False

        return True
