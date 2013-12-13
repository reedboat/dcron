"""
Stores jobs in a database table using SQLAlchemy.
"""
import pickle
import logging
import traceback

import sqlalchemy

from apscheduler.jobstores.base import JobStore
from apscheduler.job import Job

try:
    from sqlalchemy import create_engine, Table, Column, MetaData
    from sqlalchemy import Integer, DateTime, PickleType, Unicode, Sequence

except ImportError:  # pragma: nocover
    raise ImportError('SQLAlchemyJobStore requires SQLAlchemy installed')

logger = logging.getLogger(__name__)


class SQLAlchemyJobStore(JobStore):
    def __init__(self, url=None, engine=None, tablename='apscheduler_jobs', metadata=None,
                 pickle_protocol=pickle.HIGHEST_PROTOCOL):
        self.jobs = []
        self.pickle_protocol = pickle_protocol

        if engine:
            self.engine = engine
        elif url:
            self.engine = create_engine(url)
        else:
            raise ValueError('Need either "engine" or "url" defined')

        if sqlalchemy.__version__ < '0.7':
            pickle_coltype = PickleType(pickle_protocol, mutable=False)
        else:
            pickle_coltype = PickleType(pickle_protocol)
        self.jobs_t = Table(
            tablename, metadata or MetaData(),
            Column('id', Integer, Sequence(tablename + '_id_seq', optional=True), primary_key=True),
            Column('trigger', pickle_coltype, nullable=False),
            Column('script', pickle_coltype, nullable=False),
            Column('name', Unicode(1024))
            #Column('misfire_grace_time', Integer, nullable=False),
            #Column('coalesce', Boolean, nullable=False),
            #Column('max_runs', Integer),
            #Column('max_instances', Integer),
            #Column('next_run_time', DateTime, nullable=False),
            #Column('runs', BigInteger)
        )

        self.jobs_t.create(self.engine, True)

    def normalize(self, job_dict):
        row = {}
        row['id'] = job_dict['id']
        row['name'] = job_dict['name']
        row['script'] = job_dict['script']
        row['trigger'] = job_dict['trigger']
        return row


    def add_job(self, job):
        job_dict = job.__getstate__()
        job_dict = self.normalize(job_dict)
        result = self.engine.execute(self.jobs_t.insert().values(**job_dict))
        job.id = result.inserted_primary_key[0]
        self.jobs.append(job)

    def remove_job(self, job):
        delete = self.jobs_t.delete().where(self.jobs_t.c.id == job.id)
        self.engine.execute(delete)
        self.jobs.remove(job)

    def load_jobs(self):
        jobs = []
        for row in self.engine.execute(select([self.jobs_t])):
            try:
                job = Job.__new__(Job)
                job_dict = dict(row.items())
                job.__setstate__(job_dict)
                jobs.append(job)
            except Exception as e:
                print e
                traceback.print_exc(e)
                job_name = job_dict.get('name', '(unknown)')
                logger.exception('Unable to restore job "%s"', job_name)
        self.jobs = jobs
        return jobs

    def update_job(self, job):
        job_dict = job.__getstate__()
        job_dict = self.normalize(job_dict)
        update = self.jobs_t.update().where(self.jobs_t.c.id == job.id).\
            values(**job_dict)
        return self.engine.execute(update)

    def get_job(self, id):
        select = self.jobs_t.select().where(self.jobs_t.c.id == id)
        try:
            row = self.engine.execute(select).fetchone()
        except Exception as e:
            #todo
            logger.exception(e)

        if row:
            try:
                job = Job.__new__(Job)
                job_dict = dict(row.items())
                job.__setstate__(job_dict)
                return job
            except Exception:
                job_name = job_dict.get('name', 'unknown')
                logger.exception("Unable to restore job '%s'", job_name)

        return None

    def close(self):
        self.engine.dispose()

    def __repr__(self):
        return '<%s (url=%s)>' % (self.__class__.__name__, self.engine.url)
