from apscheduler.scripts import Script

class ShellScript(Script):
    def __init__(self, content):
        self.type = 'shell'

    def run(self):
        pass
