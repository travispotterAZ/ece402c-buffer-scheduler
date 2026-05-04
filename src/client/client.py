# Author: Andrew Kostick
# This client connects to the server, sends queries for a specified date range, and prints the responses.
import logging
import socket
import argparse
import threading

HOST = '127.0.0.1'
PORT = 8080


def send_query(start, end):
    """
    Connect to the server, send a query for the given date range, 
    and then print the response to the log.
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as connection:
            connection.connect((HOST, PORT))
            connection.sendall(f"QUERY weather.csv WHERE date BETWEEN {start} AND {end}\n".encode("utf-8"))
            response = connection.recv(1024).decode("utf-8")
            if response.startswith("OK"):
                logging.info("OK: %s", response.strip())
            else:
                logging.error("ERR: %s", response.strip())
    except ConnectionRefusedError:
        print("Could not connect to the server")


def main():
    """
    Definning command-line arguments, set up logging, and then starting the client threads to send queries.
    """
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default=HOST)
    ap.add_argument("--port", type=int, default=PORT)
    ap.add_argument("--start", required=True)
    ap.add_argument("--end", required=True)
    ap.add_argument("--clients", type=int, default=1)
    ap.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    args = ap.parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s [%(levelname)s] [%(threadName)s] %(name)s: %(message)s",
    )
    
    threads = []
    for i in range(args.clients):
        t = threading.Thread(target=send_query, args=(args.start, args.end))
        t.start()
        threads.append(t)
    
    for t in threads:
        t.join()

if __name__ == "__main__":
    main()