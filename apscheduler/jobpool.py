class ActiveJobPool(object):
    def __init__(self):
        self.pool = {}
        self.locks = {}

    def set_jobs(self, jobs):
        for job in jobs:
            self.add_job(job):

    def add_job(self, job):
        pass

    def remove_job(self, job_id):
        pass

    def update_job(self, job):
        pass
