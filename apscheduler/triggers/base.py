from abc import ABCMeta, abstractmethod

class Trigger(object):
    __metaclass__ = ABCMeta
    @abstractmethod
    def get_next_fire_time(self, start_date):
        pass
