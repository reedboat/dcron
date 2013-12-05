from abc import ABCMeta, abstractmethod

class Script(object):
    __metaclass__ = ABCMeta
    @abstractmethod
    def run(self):
        pass
