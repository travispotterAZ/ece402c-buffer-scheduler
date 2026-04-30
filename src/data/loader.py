# Author: Andrew Kostick
# This file contains the function to open and load the csv file then create pages of weather data based on the PAGE_SIZE.

import csv

PAGE_SIZE = 100 

def load_csv(file_path):
    pages = []
    currentPage = []

    with open(file_path, 'r') as file:
        reader = csv.DictReader(file)
        for row in reader:
            currentPage.append(row)
            if len(currentPage) == PAGE_SIZE:
                pages.append(currentPage)
                currentPage = []
            
        if currentPage:
            pages.append(currentPage)

    return pages
