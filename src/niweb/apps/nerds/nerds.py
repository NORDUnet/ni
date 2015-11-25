from lib.nmap_consumer import nmap_import

class NmapConsumer:
    def __init__(self, nerds):
        self.data = nerds

    def process(self):
        print "got data for", self.data["host"]["name"]
        nmap_import(self.data)

