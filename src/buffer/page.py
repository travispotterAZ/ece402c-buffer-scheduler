# Page object --- slot in memory holding a page from disk

# Index:       Index of the page in the buffer pool
# page_number: Unique identifier for the page
# _pinned:     Whether the page is currently pinned (in use)
# dirty:       Whether the page has been modified since it was read from disk
# state:       Used by the replacer to determine eviction eligibility

from uuid import uuid4

class Page:
    AVAILABLE  = -1
    REFERENCED =  0
    PINNED     =  1

    def __init__(self, id, size):
        self.index       = id
        self.page_number = uuid4()
        self._pinned     = 0 
        self.dirty       = False
        self.state       = Page.AVAILABLE
        self.data        = []

    def increment_pin_count(self):
        self._pinned += 1

    def decrement_pin_count(self):
        if self._pinned > 0:
            self._pinned -= 1

    def is_pinned(self):
        return self._pinned > 0

    def is_dirty(self):
        return self.dirty

    # Clearing page data and resetting metadata for reuse
    def reset(self):
        self.index       = None
        self._pinned     = 0
        self.dirty       = False
        self.state       = Page.AVAILABLE
        self.data        = []