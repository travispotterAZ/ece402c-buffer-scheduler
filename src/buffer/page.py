#Page object --- slot in memory holding a page from disk

#Index: Index of the page in the buffer pool
#Page_number: Unique identifier for the page
#Pin_Count: Number of times the page is pinned (in use)
#Dirty: Whether the page has been modified since it was read from disk
#State: Used by the replacer to determine the status of the page (e.g., available, referenced, pinned)



from uuid import uuid4 #Allows for page number generation

class Page:
    AVAILABLE  = -1
    REFERENCED =  0
    PINNED     =  1

    def __init__(self, id, size):
        self.index = id
        self.page_number = uuid4()
        self.is_pinned = 0
        self.dirty = False
        self.state = AVAILABLE
        self.data       = []

    def increment_pin_count(self):
        self.is_pinned = 1

    def decrement_pin_count(self):
        self.is_pinned = 0

    def is_dirty(self):
        return self.dirty
    
    def is_pinned(self):
        return self.is_pinned > 0
    
    #Clearing page data and resetting metadata for reuse
    def reset(self):
        self.page_id   = None
        self.pin_count = 0
        self.dirty     = False
        self.state     = Page.AVAILABLE
        self.data      = []

