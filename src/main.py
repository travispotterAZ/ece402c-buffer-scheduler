# Author: Travis Potter
# Entry point — wires CLI flags to scheduler, buffer manager, and data layer.
#
# Usage:
#   python main.py --policy fcfs --algorithm lru --frames 32 --clients 4
#
# Runs a smoke-test batch of queries against the local weather.csv, then
# prints final stats. The TCP server (server.py) will replace this loop
# once the client layer is complete.

import argparse
import os
import time

from data.loader import load_csv
from data.index import adding_index
from buffer.buffer_manager import BufferPoolManager, REPLACERS
from scheduler.scheduler import ThreadPoolScheduler, POLICIES
from interfaces import Query

# Path to weather data relative to src/
DATA_FILE = os.path.join(os.path.dirname(__file__), "data", "weather.csv")


def parse_args():
    parser = argparse.ArgumentParser(
        description="ECE 402c — Buffer Manager & Query Scheduler"
    )
    parser.add_argument(
        "--policy",
        choices=list(POLICIES),
        default="fcfs",
        help="Scheduling policy (default: fcfs)",
    )
    parser.add_argument(
        "--algorithm",
        choices=list(REPLACERS),
        default="lru",
        help="Page replacement algorithm (default: lru)",
    )
    parser.add_argument(
        "--frames",
        type=int,
        default=32,
        help="Number of buffer frames (default: 32)",
    )
    parser.add_argument(
        "--clients",
        type=int,
        default=4,
        help="Number of worker threads (default: 4)",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    print(f"[main] policy={args.policy}  algorithm={args.algorithm}  "
          f"frames={args.frames}  clients={args.clients}")

    # ── 1. Load data layer ──────────────────────────────────────────────
    print(f"[main] loading {DATA_FILE} ...")
    pages = load_csv(DATA_FILE)
    date_index = adding_index(pages)
    print(f"[main] loaded {len(pages)} pages  ({len(date_index)} date entries)")

    # ── 2. Build buffer manager ─────────────────────────────────────────
    bpm = BufferPoolManager(args.frames, algorithm=args.algorithm)
    bpm.disk_manager.load_file(DATA_FILE)
    print(f"[main] buffer pool ready — {args.frames} frames, {args.algorithm} replacer")

    # ── 3. Build scheduler ──────────────────────────────────────────────
    policy = POLICIES[args.policy](maxsize=500)
    scheduler = ThreadPoolScheduler(
        policy=policy,
        workers=args.clients,
        queue_size=500,
        reject_when_full=False,
        buffer_manager=bpm,
        date_index=date_index,
    )
    scheduler.start()
    print(f"[main] scheduler started — {args.clients} workers, {args.policy} policy")

    # ── 4. Smoke-test query batch ────────────────────────────────────────
    # Queries span the full 2018-2023 dataset to exercise all pages.
    # Replace this section with server.py once the TCP layer is ready.
    queries = [
        Query("2018-01-01", "2018-06-30", client_id="client-A"),
        Query("2019-01-01", "2019-06-30", client_id="client-B"),
        Query("2020-01-01", "2020-06-30", client_id="client-C"),
        Query("2021-01-01", "2021-06-30", client_id="client-D"),
        Query("2022-01-01", "2022-06-30", client_id="client-A"),
        Query("2023-01-01", "2023-06-30", client_id="client-B"),
        # Overlapping ranges — should produce buffer hits
        Query("2018-03-01", "2018-09-30", client_id="client-C"),
        Query("2020-03-01", "2020-09-30", client_id="client-D"),
    ]

    for query in queries:
        accepted = scheduler.submit(query)
        status = "accepted" if accepted else "rejected"
        print(f"[main] query {query.query_id} ({query.start_date} → {query.end_date}) {status}")

    # ── 5. Wait for queries to drain, then print final stats ─────────────
    time.sleep(len(queries) * 0.5 + 2.0)
    scheduler.stop()

    stats = scheduler.get_stats()
    print("\n── Final stats ──────────────────────────────────────────────")
    print(f"  queries processed : {stats['processed']}")
    print(f"  avg latency       : {stats['avg_latency_ms']:.2f} ms")
    print(f"  throughput        : {stats['rps']:.2f} queries/sec")
    print(f"  page hits         : {stats['page_hits']}")
    print(f"  page faults       : {stats['page_faults']}")
    hit_rate = (
        stats['page_hits'] / (stats['page_hits'] + stats['page_faults']) * 100
        if (stats['page_hits'] + stats['page_faults']) > 0 else 0.0
    )
    print(f"  buffer hit rate   : {hit_rate:.1f}%")
    print("─────────────────────────────────────────────────────────────")


if __name__ == "__main__":
    main()