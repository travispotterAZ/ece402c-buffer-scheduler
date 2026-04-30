#Page object --- slot in memory holding a page from disk

#Index: Index of the page in the buffer pool
#Page_number: Unique identifier for the page
#Pin_Count: Number of times the page is pinned (in use)
#Dirty: Whether the page has been modified since it was read from disk
#State: Used by the replacer to determine the status of the page (e.g., available, referenced, pinned)



from uuid import uuid4 #Allows for page number generation

class Page:

    def __init__(self, id, size):
        self.index = id
        self.page_number = uuid4()
        self.pin_count = 0
        self.dirty = False
        self.state = -1

    def increment_pin_count(self):
        self.pin_count += 1

    def decrement_pin_count(self):
        self.pin_count -= 1

    def is_dirty(self):
        return self.dirty

    def get_pin_count(self):
        return self.pin_count
