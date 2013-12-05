import urllib2

from apscheduler.scripts import Script

class HttpScript(Script):
    def __init__(self, url, method='GET'):
        self.type = 'http'
        self.url  = url
        self.method = method

    def run(self):
        return urllib2.urlopen(self.url).read()
