# Author: Andrew Kostick
# This file contains the function to assign indices to rows from the loaded CSV data.

def adding_index(pages):
    indexed_pages = {}
    for i, page in enumerate(pages):
        for row in page:
            date = row['DATE']
            indexed_pages[date] = i

    return indexed_pages
