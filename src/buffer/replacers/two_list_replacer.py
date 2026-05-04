# Author: Travis Potter
# Two List Algorithm --- maintain two lists of pages: one for recently referenced
# pages and one for less recently referenced pages.

from collections import OrderedDict
from buffer.replacers.replacer import Replacer
from buffer.page import Page


class TwoListReplacer(Replacer):

    # Constructor
    def __init__(self, hot_ratio=0.4):
        # Hot Ratio defines what % of pages in buffer can be "hot pages"
        # (i.e. active list); default to 40% hot pages
        super().__init__()
        self.hot_ratio   = hot_ratio
        self._inactive   = OrderedDict()
        self._active     = OrderedDict()
        self._location   = dict()
        self.frame_table = []

    def _get_page(self, page_id):
        """Look up a Page object from frame_table by its index."""
        for page in self.frame_table:
            if page.index == page_id:
                return page
        return None

    def insert(self, page):
        total      = len(self.frame_table)
        active_cap = int(self.hot_ratio * total)

        # Page is already being tracked
        if page.index in self._location:

            # Case 1: in inactive list → promote to active list
            if self._location[page.index] == 'inactive':
                del self._inactive[page.index]
                self._active[page.index] = page
                self._location[page.index] = 'active'
                self._balance_active(active_cap)

            # Case 2: already in active list → move to back (most recently used)
            else:
                self._active.move_to_end(page.index)

            page.state = Page.REFERENCED

        # Page is not yet tracked → add to inactive list
        else:
            if page.index is not None:
                self._inactive[page.index] = page
                self._location[page.index] = 'inactive'
            page.state = Page.AVAILABLE

    # Maintain hot ratio — demote oldest active pages to inactive when over cap
    def _balance_active(self, active_cap):
        while len(self._active) > active_cap:
            victim_id, victim_page = self._active.popitem(last=False)
            self._inactive[victim_id] = victim_page
            self._location[victim_id] = "inactive"

    # Identify victim page for eviction
    def victim(self):
        # If inactive list is empty, demote the oldest active page first
        if not self._inactive:
            if not self._active:
                return None  # both lists empty — no victim available

            victim_id, victim_page = self._active.popitem(last=False)
            self._inactive[victim_id] = victim_page
            self._location[victim_id] = "inactive"

        checked = 0

        # Scan inactive list for the oldest non-pinned page
        while self._inactive and checked < len(self._inactive):
            victim_id = next(iter(self._inactive))
            page = self._get_page(victim_id)

            if page and page.is_pinned():
                # Skip pinned pages — rotate to back and keep looking
                self._inactive.move_to_end(victim_id)
                checked += 1
                continue

            self._inactive.pop(victim_id)
            del self._location[victim_id]
            return page

        return None  # all inactive pages are pinned

    def erase(self, page):
        if page.index in self._location:
            location = self._location[page.index]
            if location == "inactive":
                self._inactive.pop(page.index, None)
            else:
                self._active.pop(page.index, None)
            del self._location[page.index]
            return True
        return False

    def __len__(self):
        return len(self._active) + len(self._inactive)