#Layer talking to files on disk
# -Handles files
# - Other layers ask this layer to read/write pages to disk

class DiskManager:

    def __init__(self, page_size):
        self.page_size = page_size

    def readPage(self, page_id):
        pass

    def writePage(self, page):
        pass

    def allocatePage(self):
        pass

    def deAllocatePage(self, page):
        pass
