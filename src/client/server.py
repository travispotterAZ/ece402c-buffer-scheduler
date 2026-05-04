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
from interfaces import Query, Task

HOST = '127.0.0.1'
PORT = 8080

# Absolute path so server can be launched from any working directory
DATA_FILE = os.path.join(os.path.dirname(__file__), '..', 'data', 'weather.csv')

# Load the weather data from csv and build date index
pages = load_csv(DATA_FILE)
index = adding_index(pages)
print(f"Loaded {len(pages)} pages, {len(index)} dates indexed")

# Initialize buffer pool with LRU (best performer from benchmark results)
# and enough frames to hold the full dataset
buffer_pool = BufferPoolManager(len(pages), algorithm='lru')
buffer_pool.disk_manager.load_file(DATA_FILE)

# Pre-load all pages into the buffer pool so first queries are served from memory
for i, page_data in enumerate(pages):
    frame = buffer_pool.buffer_pool[i]
    frame.data = page_data
    frame.index = i
    buffer_pool.page_map[i] = i

# Initialize scheduler with FCFS (lowest latency from benchmark results)
policy = FCFSScheduler()
scheduler = ThreadPoolScheduler(policy=policy, buffer_manager=buffer_pool, date_index=index)
scheduler.start()


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
            if 'BETWEEN' not in parts:
                return "ERR wrong QUERY format"

            between_idx = parts.index('BETWEEN')
            and_idx     = parts.index('AND')

            start_date = parts[between_idx + 1]
            end_date   = parts[and_idx + 1]

            query  = Query(start_date=start_date, end_date=end_date)
            accept = scheduler.submit(query)

            if not accept:
                return "ERR server in use"
        else:
            return f"ERR invalid command: {op}"

        return f"OK query accepted: {start_date} to {end_date}"

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