import subprocess

from apscheduler.scripts import Script

class CommandScript(Script):
    def __init__(self, command):
        self.type = 'command'
        self.command = command

    def run(self):
        #return subprocess.check_output(self.content.split())
        ##
        retcode = subprocess.check_call(self.command.split())
        if retcode > 0:
            return False
        return True
