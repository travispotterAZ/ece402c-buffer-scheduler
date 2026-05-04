# Author: Andrew Kostick
#
# Co-Author: Travis Potter
#
# This file contains the function to assign indices to rows from the loaded CSV data.

from datetime import datetime

def adding_index(pages):
    indexed_pages = {}
    for i, page in enumerate(pages):
        for row in page:
            date = row['DATE']
            indexed_pages[date] = i

    return indexed_pages

def get_page_ids_for_range(index, start_date, end_date):
    """
    Return a list of pages covering the input date range
    [start_date, end_date] inclusive.
 
    Parameters
    ----------
    index      : dict returned by adding_index()  {date_str -> page_id}
    start_date : str  e.g. "2020-01-01"
    end_date   : str  e.g. "2020-06-30"
    """

    start = datetime.fromisoformat(start_date) #constructing a date object from a string
    end   = datetime.fromisoformat(end_date)
 
    seen = set()    # tracks unique page IDs so no duplicates are returned
    page_ids = []
 
    for date_str, page_id in index.items():
        date = datetime.fromisoformat(date_str)
        if start <= date <= end:
            if page_id not in seen:
                seen.add(page_id)
                page_ids.append(page_id)
 
    return sorted(page_ids)