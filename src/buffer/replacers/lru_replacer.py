#Author: Sourced Material from GitHub
#LRU Algorithm --- evict the least recently used page when a victim is needed
# - Uses a circular list to track the state of pages in the buffer pool


from buffer.page import Page
from buffer.replacers.replacer import Replacer

class LRUReplacer(Replacer):

    def __init__(self, buffer_manager):
        super().__init__()
        self.no_of_buffers = len(buffer_manager)
        self.frame_table = buffer_manager.getFrameTable()

        for frames in self.frame_table:
            frames.state = Page.AVAILABLE

        self.head = -1

    def insert(self, page):
        page.state = Page.REFERENCED

    def victim(self):
        if self.frame_table:
            for i in range(2 * len(self.frame_table)):
                self.head = (self.head + 1) % len(self.frame_table)

                if self.frame_table[self.head].state == Page.REFERENCED:
                    self.frame_table[self.head].state = Page.AVAILABLE

                elif self.frame_table[self.head].state == Page.AVAILABLE:
                    return self.frame_table[self.head]

        return None

    def erase(self, page):
        index = -1
        for frames in self.frame_table:
            index += 1
            if frames.index == page.index:
                self.frame_table.pop(index)
                return True
        return False

    def __len__(self):
        return self.no_of_buffers
