# Author: Travis Potter
# Benchmark runner — tests all combinations of scheduling policy and
# replacement algorithm across varying frame counts and client counts.
#
# Usage (from src/):
#   python benchmark/runner.py
#
# Results are written to benchmark/results/results.json and printed
# as a summary table. Pass that file to benchmark/plots.py to generate graphs.

import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.loader import load_csv
from data.index import adding_index
from buffer.buffer_manager import BufferPoolManager, REPLACERS
from scheduler.scheduler import ThreadPoolScheduler, POLICIES
from interfaces import Query

# ── Configuration ─────────────────────────────────────────────────────────────

DATA_FILE   = os.path.join(os.path.dirname(__file__), "..", "data", "weather.csv")
RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results")

# Frame counts well below the 15-page dataset to create real eviction pressure
FRAME_COUNTS  = [4, 8, 12]
CLIENT_COUNTS = [2, 4, 8]

# Large, varied query set — mix of short, medium, long, and overlapping ranges.
# More queries + shorter ranges = more page fetches = meaningful eviction differences.
QUERY_DEFINITIONS = [
    # Short single-month queries (1 page each) — high repetition creates hit opportunities
    ("2018-01-01", "2018-01-31", "client-A", 1),
    ("2018-02-01", "2018-02-28", "client-B", 1),
    ("2018-03-01", "2018-03-31", "client-C", 1),
    ("2018-04-01", "2018-04-30", "client-D", 1),
    ("2018-05-01", "2018-05-31", "client-A", 1),
    ("2018-06-01", "2018-06-30", "client-B", 1),
    ("2018-07-01", "2018-07-31", "client-C", 1),
    ("2018-08-01", "2018-08-31", "client-D", 1),
    ("2018-09-01", "2018-09-30", "client-A", 1),
    ("2018-10-01", "2018-10-31", "client-B", 1),
    ("2018-11-01", "2018-11-30", "client-C", 1),
    ("2018-12-01", "2018-12-31", "client-D", 1),
    # Medium two-month queries — cross page boundaries
    ("2018-01-15", "2018-03-15", "client-A", 3),
    ("2018-03-15", "2018-05-15", "client-B", 3),
    ("2018-05-15", "2018-07-15", "client-C", 3),
    ("2018-07-15", "2018-09-15", "client-D", 3),
    ("2018-09-15", "2018-11-15", "client-A", 3),
    # Long quarter queries — span 3-4 pages, stress eviction at low frame counts
    ("2018-01-01", "2018-03-31", "client-B", 5),
    ("2018-04-01", "2018-06-30", "client-C", 5),
    ("2018-07-01", "2018-09-30", "client-D", 5),
    ("2018-10-01", "2018-12-31", "client-A", 5),
    # Repeat short queries — these should be buffer hits if replacer works well
    ("2018-01-01", "2018-01-31", "client-B", 1),
    ("2018-06-01", "2018-06-30", "client-C", 1),
    ("2018-12-01", "2018-12-31", "client-D", 1),
    # Overlapping ranges — intentionally re-request pages already in buffer
    ("2018-01-10", "2018-02-10", "client-A", 2),
    ("2018-06-10", "2018-07-10", "client-B", 2),
    ("2018-11-10", "2018-12-10", "client-C", 2),
]


def build_queries():
    return [
        Query(start, end, client_id=cid, priority=pri)
        for start, end, cid, pri in QUERY_DEFINITIONS
    ]


# ── Active drain ──────────────────────────────────────────────────────────────

def drain(scheduler, total_queries, timeout=60.0):
    """
    Wait until all submitted queries have been processed or timeout is reached.
    Polls every 100ms instead of sleeping a fixed large duration.
    """
    deadline = time.time() + timeout
    while time.time() < deadline:
        with scheduler._lock:
            processed = scheduler._processed
        if processed >= total_queries:
            return
        time.sleep(0.1)


# ── Run one combination ───────────────────────────────────────────────────────

def run_combination(policy_name, algorithm_name, frames, clients, date_index):
    policy = POLICIES[policy_name](maxsize=500)

    bpm = BufferPoolManager(frames, algorithm=algorithm_name)
    bpm.disk_manager.load_file(DATA_FILE)

    scheduler = ThreadPoolScheduler(
        policy=policy,
        workers=clients,
        queue_size=500,
        reject_when_full=False,
        buffer_manager=bpm,
        date_index=date_index,
    )
    scheduler.start()

    queries = build_queries()
    accepted = 0
    for query in queries:
        if scheduler.submit(query):
            accepted += 1

    # Active drain — exits as soon as all accepted queries are processed
    drain(scheduler, accepted, timeout=60.0)
    scheduler.stop()

    stats = scheduler.get_stats()
    stats["policy"]    = policy_name
    stats["algorithm"] = algorithm_name
    stats["frames"]    = frames
    stats["clients"]   = clients
    stats["accepted"]  = accepted

    total_pages = stats["page_hits"] + stats["page_faults"]
    stats["hit_rate"] = (
        stats["page_hits"] / total_pages * 100 if total_pages > 0 else 0.0
    )

    return stats


# ── Formatting ────────────────────────────────────────────────────────────────

def print_row(s):
    print(
        f"  {s['policy']:<10} {s['algorithm']:<12} "
        f"frames={s['frames']:<4} clients={s['clients']:<3} "
        f"queries={s['processed']:<4} "
        f"avg_ms={s['avg_latency_ms']:>7.2f} "
        f"hits={s['page_hits']:<5} faults={s['page_faults']:<5} "
        f"hit_rate={s['hit_rate']:>5.1f}%"
    )


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("[runner] loading data ...")
    pages      = load_csv(DATA_FILE)
    date_index = adding_index(pages)
    print(f"[runner] {len(pages)} pages, {len(date_index)} date entries")
    print(f"[runner] {len(QUERY_DEFINITIONS)} queries per run\n")

    os.makedirs(RESULTS_DIR, exist_ok=True)

    all_results = []
    total_runs  = len(POLICIES) * len(REPLACERS) * len(FRAME_COUNTS) * len(CLIENT_COUNTS)
    run_num     = 0

    for policy_name in POLICIES:
        for algorithm_name in REPLACERS:
            for frames in FRAME_COUNTS:
                for clients in CLIENT_COUNTS:
                    run_num += 1
                    print(
                        f"[runner] run {run_num}/{total_runs} — "
                        f"policy={policy_name}  algorithm={algorithm_name}  "
                        f"frames={frames}  clients={clients}"
                    )

                    try:
                        stats = run_combination(
                            policy_name, algorithm_name,
                            frames, clients,
                            date_index,
                        )
                        all_results.append(stats)
                        print_row(stats)

                    except Exception as e:
                        print(f"  [ERROR] {e}")

                    print()

    # Write results JSON
    results_path = os.path.join(RESULTS_DIR, "results.json")
    with open(results_path, "w") as f:
        json.dump(all_results, f, indent=2)
    print(f"[runner] results written to {results_path}")

    # Summary tables
    print("\n── Summary: avg latency and hit rate by algorithm ──────────────────")
    for alg in REPLACERS:
        subset = [r for r in all_results if r["algorithm"] == alg]
        if subset:
            avg_ms  = sum(r["avg_latency_ms"] for r in subset) / len(subset)
            avg_hit = sum(r["hit_rate"]        for r in subset) / len(subset)
            print(f"  {alg:<12}  avg_latency={avg_ms:>7.2f} ms  avg_hit_rate={avg_hit:>5.1f}%")

    print("\n── Summary: avg latency by policy ──────────────────────────────────")
    for pol in POLICIES:
        subset = [r for r in all_results if r["policy"] == pol]
        if subset:
            avg_ms = sum(r["avg_latency_ms"] for r in subset) / len(subset)
            print(f"  {pol:<10}  avg_latency={avg_ms:>7.2f} ms")


if __name__ == "__main__":
    main()