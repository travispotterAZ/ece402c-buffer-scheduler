# Author: Travis Potter
# Layer talking to files on disk
# - Handles reading/writing pages to and from the CSV data file
# - Translates logical page_id to row ranges in the CSV
# - Other layers ask this layer to read/write pages to disk

import csv
from buffer.page import Page

PAGE_SIZE = 100  # Must match loader.py


class DiskManager:

    def __init__(self, page_size=PAGE_SIZE):
        self.page_size = page_size
        self._file_path = None
        self._pages = []          # list of pages; each page is a list of row dicts
        self._allocated = set()   # tracks page_ids that have been allocated

    # ------------------------------------------------------------------
    # File management
    # ------------------------------------------------------------------

    def load_file(self, file_path):
        """
        Load a CSV file from disk, partitioning rows into fixed-size pages.
        Must be called before any readPage/writePage calls.
        """
        self._file_path = file_path
        self._pages = []

        with open(file_path, newline='') as f:
            reader = csv.DictReader(f)
            current_page = []

            for row in reader:
                current_page.append(row)
                if len(current_page) == self.page_size:
                    self._pages.append(current_page)
                    current_page = []

            if current_page:
                self._pages.append(current_page)

        self._allocated = set(range(len(self._pages)))

    def page_count(self):
        """Return total number of pages on disk."""
        return len(self._pages)

    # ------------------------------------------------------------------
    # Core page I/O
    # ------------------------------------------------------------------

    def readPage(self, page_id, frame=None):
        """
        Read a page from disk by page_id.

        If a frame (Page object) is supplied, its data is updated in-place
        and the frame is returned — this is the path BufferPoolManager uses
        when loading into an evicted slot.

        If no frame is supplied, a new Page object is created and returned —
        useful for testing or one-off reads.
        """
        if page_id < 0 or page_id >= len(self._pages):
            raise ValueError(f"page_id {page_id} out of range (0..{len(self._pages) - 1})")

        rows = self._pages[page_id]

        if frame is not None:
            frame.data = rows
            return frame

        page = Page(page_id, self.page_size)
        page.data = rows
        return page

    def writePage(self, page):
        """
        Write a page back to disk (into the in-memory page store).

        Method is never used as project is for READ-ONLY funtionality,
        but implemented in case of fututure extion for use of the dirty bit tracking.
        """
        if page.index is None:
            return

        if page.index < len(self._pages):
            self._pages[page.index] = page.data
        else:
            # Page is beyond current bounds — extend the store
            while len(self._pages) <= page.index:
                self._pages.append([])
            self._pages[page.index] = page.data

    def allocatePage(self):
        """
        Allocate a new empty page at the end of the page store.
        Returns a Page object with the new page_id.
        """
        page_id = len(self._pages)
        self._pages.append([])
        self._allocated.add(page_id)

        page = Page(page_id, self.page_size)
        return page

    def deAllocatePage(self, page):
        """
        Mark a page as deallocated and clear its data.
        The slot is kept in the list to avoid shifting page_ids.
        """
        if page.index in self._allocated:
            self._pages[page.index] = []
            self._allocated.discard(page.index)