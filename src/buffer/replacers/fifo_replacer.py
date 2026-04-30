#Author: Travis Potter
#FIFO Algorithm --- evict the first page that was loaded into the buffer pool when a victim is needed



from collections import deque
from buffer import page
from buffer.replacers.replacer import Replacer
from buffer.page import Page


class FIFOReplacer(Replacer):                                   # First In First Out sublcass of Replacer

    #Constructor
    def __init__(self):
        super().__init__()                                      #Parent Constructor Call
        self.queue = deque()                                    #Double-ended queue for page management
        self.in_queue = set()                                   #Track pages currently in queue for uniqueness & O(1) lookups
        self.frame_table = []                                   #Reference to buffer manager's frame table for page state management

    #New page insertion into queue
    def insert(self, page):
        if page.index not in self.in_queue:
            self.queue.append(page.index) 
            self.in_queue.add(page.index)
        
        page.state = Page.REFERENCED

    #Idendity victim page for eviction
    def victim(self):
        if not self.frame_table or not self.queue:
            return None                                         #No victim if frame table is empty or no pages in queue
    
        checked = 0; #for stats
        while self.queue and checked < len(self.queue):
            frame_index = self.queue[0]                         #Grab front of queue
            page = self.frame_table[frame_index]                #Get page in that frame

            if page is None:                                    #Check if frame is empty
                self.queue.popleft()
                self.in_queue.remove(frame_index)
                continue
            

            if page.is_pinned():                                #If page is pinned (i.e. in use on disk)
                self.queue.rotate(-1) 
                checked += 1
                continue

            self.queue.popleft()
            self.in_queue.remove(frame_index)
            return page
        
        return 
    
    #Removes a page from queue
    def erase(self, page):
        if page.index in self.in_queue:
            self.queue.remove(page.index)
            self.in_queue.remove(page.index)
            return True
        return False
    
    def __len__(self):
        return len(self.queue)



    