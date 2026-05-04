# Author: Travis Potter
# Brain of system
# - Coordination of disk and buffer pool

from buffer.replacers.lru_replacer import LRUReplacer
from buffer.replacers.fifo_replacer import FIFOReplacer
from buffer.replacers.two_list_replacer import TwoListReplacer
from buffer.page import Page
from buffer.disk_manager import DiskManager

REPLACERS = {
    "lru":      LRUReplacer,
    "fifo":     FIFOReplacer,
    "two_list": TwoListReplacer,
}


class BufferPoolManager:

    #algorithm can be "lru", "fifo", or "two_list"
    def __init__(self, no_of_pages, algorithm="lru"):
        self.no_of_pages = no_of_pages  # must be set first — LRUReplacer calls len(self) on construction
        self.buffer_pool = []
        self.disk_manager = DiskManager()

        for i in range(no_of_pages):
            self.buffer_pool.append(Page(i, 100))  # Page size matches loader.py PAGE_SIZE

        # Select replacer by algorithm name
        if algorithm not in REPLACERS:
            raise ValueError(f"Unknown algorithm '{algorithm}'. Choose from: {list(REPLACERS)}")

        replacer_cls = REPLACERS[algorithm]

        # LRUReplacer expects the buffer manager; FIFO and TwoList take no args
        if algorithm == "lru":
            self.replacer = replacer_cls(self)
        else:
            self.replacer = replacer_cls()

        self.replacer.frame_table = self.buffer_pool  # wire frame_table for all replacers
        self.page_map = {}  # page_id -> frame index in buffer_pool

        # Pre-populate the replacer with all frames so they are available for eviction
        # from the first fetchPage call. LRU scans frame_table directly so it doesn't
        # strictly need this, but FIFO and Two-List rely on their internal queues.
        for page in self.buffer_pool:
            self.replacer.insert(page)

    def __len__(self):
        return self.no_of_pages

    def getFrameTable(self):
        return self.buffer_pool

    def newPage(self):
        page = self.disk_manager.allocatePage()
        page.increment_pin_count()
        return page

    def fetchPage(self, page_id):
        # Check if page is already in the buffer pool
        if page_id in self.page_map:
            frame_idx = self.page_map[page_id]
            page = self.buffer_pool[frame_idx]
            page.increment_pin_count()
            self.replacer.insert(page)
            return page

        # Page not in buffer pool — find a victim frame to evict
        victim = self.replacer.victim()
        if victim is None:
            return None  # All frames are pinned; cannot fetch

        # Write the victim back to disk if it was modified
        if victim.is_dirty():
            self.disk_manager.writePage(victim)

        # Remove the evicted page from the page map
        if victim.index in self.page_map:
            del self.page_map[victim.index]

        # Find which slot the victim occupies and load new page data into it
        frame_idx = self.buffer_pool.index(victim)
        self.disk_manager.readPage(page_id, victim)

        # Update the frame's metadata
        victim.index = page_id
        victim.dirty = False
        victim.increment_pin_count()
        self.replacer.insert(victim)

        # Register the new page in the map
        self.page_map[page_id] = frame_idx

        return victim

    def unpinPage(self, page_id, is_dirty):
        if page_id not in self.page_map:
            return False

        frame_idx = self.page_map[page_id]
        page = self.buffer_pool[frame_idx]
        page.decrement_pin_count()

        if is_dirty:
            page.dirty = True

        # Once unpinned, the replacer can consider this frame for eviction
        if not page.is_pinned():
            self.replacer.insert(page)

        return True

    def flushPage(self, page_id):
        if page_id not in self.page_map:
            return False

        frame_idx = self.page_map[page_id]
        self.disk_manager.writePage(self.buffer_pool[frame_idx])
        return True

    def flushAllPages(self):
        for page in self.buffer_pool:
            self.disk_manager.writePage(page)

    def deletePage(self, page_id):
        if page_id not in self.page_map:
            return False

        frame_idx = self.page_map[page_id]
        page = self.buffer_pool[frame_idx]

        if page.is_pinned():
            raise ValueError(f"Cannot delete page {page_id}: page is still pinned")

        self.replacer.erase(page)
        self.disk_manager.deAllocatePage(page)
        del self.page_map[page_id]
        page.reset()

        return True