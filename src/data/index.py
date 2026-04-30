
def adding_index(pages):
    indexed_pages = {}
    for i, page in enumerate(pages):
        for row in page:
            date = row['DATE']
            indexed_pages[date] = i

    return indexed_pages





if __name__ == "__main__":
    from loader import load_csv
    
    pages = load_csv('data/weather.csv')
    index = adding_index(pages)
    
    for date, page_id in list(index.items())[:20]:
        print(f"Date: {date} -> Page: {page_id}")
    
    print(f"\nTotal dates indexed: {len(index)}")
    print(f"Total pages: {len(pages)}")