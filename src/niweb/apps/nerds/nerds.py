from lib.noclook_nmap_consumer import insert_nmap

class NmapConsumer:
    def __init__(self, nerds):
        self.data = nerds

    def process(self):
        print "got data for", self.data["host"]["name"]

