from apscheduler.reporters.base import Reporter

class SQLAlchemyReporter(Reporter):
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
            Column('failed', Integer, nullable=False),
            Column('missed', Integer, nullable=False),
            Column('succed', Integer, nullable=False),
            Column('last_run_time', Datetime, nullable=False),
            Column('next_run_time', Datetime)
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
                "succed": 0,
                "failed": 0,
                'missed': 0,
                'last_run_time': None,
                'next_run_time': None,
                'is_record': False, 
            }

    def report(self, job_id, status, run_time, next_run_time):
        running_dict = self.get(job_id)
        is_record = False if running_dict.has_key('is_record') else True
        if status:
            running_dict[status] += 1
        running_dict['last_run_time'] = last_run_time
        running_dict['next_run_time'] = next_run_time
        if is_record:
            sql = self.records_t.insert().values(**running_dict)
            result = self.engine.execute(sql)
        else:
            del running_dict['is_record']
            sql = self.records_t.update().where(self.records_t.c.job_id=job_id).values(**running_dict)
            result = self.engine.execute(sql)
        return True
