#Author: Travis Potter
#Two List Algorithm --- maintain two lists of pages: one for recently referenced pages and one for less recently referenced pages.

from collections import OrderedDict
from buffer import page
from buffer.replacers.replacer import Replacer
from buffer.page import Page


class TwoListReplacer(Replacer):

    #Constructor
    def __init__(self, hot_ratio = 0.4):                                  #Hot Ratio defines what % of pages in buffer can be "hot pages" (i.e. active list) ; default to 40% hot pages
        super().__init__()
        self.hot_ratio    = hot_ratio
        self._inactive    = OrderedDict()
        self._active      = OrderedDict()
        self._location    = dict()
        self.frame_table  = []

    def insert(self, page):
        total = len(self.frame_table)
        active_cap = int(self.hot_ratio * len(self.frame_table))
        inactive_cap = total - active_cap

        #Page is being tracked
        if page.index in self._location:

            #Case #1: Page in the "inactive" list --> Move to "active" list
            if self._location[page.index] == 'inactive':
                del self._inactive[page.index]                          #Remove from inactive list
                self._active[page.index] = page                         #Insert into active list
                self._location[page.index] = 'active'                   #Update Location

            #Case #2: Page in "active" list --> Move to back of "active list"
            else:
                self._active.move_to_end(page.index)                      #Move to back of active list
            
            page.state = Page.REFERENCED
        
        #Page is not being tracked
        else:
            if page.index is not None:
                self._inactive[page.index] = None                      #Insert placeholder into inactive list
                self._location[page.index] = 'inactive'                #Track location as inactive
            page.state = Page.AVAILABLE

    #Maintain hot ratio in active list
    def _balance_active(self, active_cap):
        while len(self._active) > active_cap:
            victim_id = self._active.popitem(last=False)[0]
            self._inactive[victim_id] = None
            self._location[victim_id] = "inactive"

    #Identify victim page for eviction
    def victim(self):
        if not self._inactive:
            if not self._active:
                return None                                         #No victim if both lists are empty

            victim_id = self._active.popitem(last=False)[0]         #Demote oldest active page to inactive list
            self._inactive[victim_id] = None
            self._location[victim_id] = "inactive"

        checked = 0

        while self._inactive and checked < len(self._inactive):     #Look for non-pinned vitim in inactive list
            victim_id = next(iter(self._inactive))                  #peek oldest
            page = self._get_page(victim_id)

            if page and page.is_pinned():                           #if page is pinned, mvoe to back of inactive list and check next
                self._inactive.move_to_end(victim_id)
                checked += 1
                continue

            self._inactive.pop(victim_id)                           #evict victim from inactive list
            del self._location[victim_id]
            
            return page

        return None
    
    def erase(self, page):
        if page.index in self._location:                            #Check poage is being tracked, then remove from appropriate list
            location = self._location[page.index]
            if location == "inactive":
                self._inactive.pop(page.index, None)
                del self._location[page.index]

            else:
                self._active.pop(page.index, None)
                del self._location[page.index]

            return True
        return False
    
    def __len__(self):
        return len(self._active) + len(self._inactive)
    
    

            

