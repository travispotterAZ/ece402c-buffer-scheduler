# Author: Andrew Kostick
# This server listens for incoming client connections, processes queries, and sends responses
import socket
import threading
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from data.loader import load_csv
from data.index import adding_index
from buffer.buffer_manager import BufferPoolManager
from scheduler.scheduler import ThreadPoolScheduler
from scheduler.fcfs import FCFSScheduler
from interfaces import Query

HOST = '127.0.0.1'
PORT = 8080

# Initialize scheduler with FCFS and start the worker threads
policy = FCFSScheduler()
scheduler = ThreadPoolScheduler(policy=policy)
scheduler.start()

# Initialize buffer pool with 32 frames
buffer_pool = BufferPoolManager(32)

# Load The weather data from csv and build date index
pages = load_csv('data/weather.csv')
index = adding_index(pages)
print(f"Loaded {len(pages)} pages, {len(index)} dates indexed")

def handle_query(line: str) -> str:
    """
    Parse the query and check if it is valid.
    Submit the query to the scheduler, find matching pages
    from the index, fetch them from the buffer pool, and return the response.
    """
    line = line.strip()
    if not line:
        return "ERR empty request"

    parts = line.split()
    op = parts[0].upper()

    try:
        if op == 'QUERY':
            if len(parts) < 8:
                return "the QUERY requires a date argument"
            
            start_date = parts[5]
            end_date = parts[7]

            query = Query(start_date=start_date, end_date=end_date)
            scheduler.submit(query)

            matching_pages = set()
            for date, page_id in index.items():
                if start_date <= date <= end_date:
                    matching_pages.add(page_id)

            results = []
            for page_id in matching_pages:
                page = buffer_pool.fetchPage(page_id)
                results.append(page)

            if matching_pages:
                return f"OK {len(matching_pages)} pages found: {', '.join(map(str, matching_pages))}"
            else:
                return "OK no pages found"
    except (ValueError, IndexError):
        return "ERR invalid argument"


def handle_client(conn, addr):
    """
    Handle an individual client connection.
    Receives queries, processes them, and sends responses back.
    """
    print(f"Connected by {addr}")
    with conn:
        while True:
            try:
                data = conn.recv(1024)
                if not data:
                    break
                print(f"Query from {addr}: {data.decode().strip()}")
                response = handle_query(data.decode())
                print(f"Response: {response}")
                conn.sendall((response + "\n").encode())
            except (ConnectionResetError, OSError):
                break
    print(f"Disconnected {addr}")


def start_server():
    """
    Start the TCP server and listen for incoming connections.
    Each client gets its own thread.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((HOST, PORT))
        s.listen()
        print(f"Server listening on {HOST}:{PORT}")
        while True:
            conn, addr = s.accept()
            threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()

if __name__ == "__main__":
    start_server()  