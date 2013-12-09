from abc import ABCMeta, abstractmethod

class Reporter(object):
    __metaclass__ = ABCMeta

    @abstractmethod
    def report(self, job_id, status, run_time, next_run_time=None, job=None):
        '''
        汇报运行状态. 成功、失败、未执行.
        本次执行时间、下次执行时间
        '''
        pass


    def query(self, job_id):
        pass
