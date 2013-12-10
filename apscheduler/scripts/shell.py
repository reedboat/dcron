import subprocess

from apscheduler.scripts import Script

class ShellScript(Script):
    def __init__(self, content):
        self.type = 'shell'

    def run(self):
        #return subprocess.check_output(self.content.split())
        ##
        retcode = subprocess.check_call(self.content.split())
        if retcode > 0:
            return False
        return True
