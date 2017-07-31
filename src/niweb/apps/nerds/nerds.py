from .lib.nmap_consumer import nmap_import
import logging
logger = logging.getLogger(__name__)

class NmapConsumer:
    def __init__(self, nerds):
        self.data = nerds

    def process(self):
        try:
            nmap_import(self.data)
        except:
            name = self.data.get("host", {}).get("name")
            logger.exception("Unable to process %s" % name)
            raise

