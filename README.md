# ECE 402c — OS Buffer Management & Query Scheduler

**Team:** Travis Potter · Ryan Brass · Andrew Kostick  
**Course:** ECE 402c — Operating System Design · Spring 2026

---

## Overview

This project implements a simulated OS buffer manager and query scheduler in Python, applying core OS memory and I/O design principles to concurrent date-range queries over NOAA global weather records (Bardufoss, Norway — 2018 to 2023, 2189 days, 22 pages).

The system is built in four cooperating layers that mirror real OS components:

- **TCP Client Layer** — simulates processes issuing date-range queries over a network socket
- **Process Scheduler** — delegates queries to worker threads via configurable scheduling policies (FCFS, Round Robin, Priority)
- **Paged Buffer Cache** — manages a fixed pool of memory frames using configurable replacement algorithms (LRU, FIFO, Two-List)
- **File System Layer** — translates logical page addresses to rows in the CSV on disk

---

## Requirements

- Python 3.10+
- `matplotlib` (for benchmark graphs only)

```bash
pip install matplotlib
```

---

## Project Structure

```
src/
├── main.py                          # Entry point — CLI flags, smoke test
├── interfaces.py                    # Shared Query and Task dataclasses
│
├── buffer/
│   ├── buffer_manager.py            # Frame pool, pin/unpin, page map, replacer wiring
│   ├── disk_manager.py              # CSV loader, page I/O, byte-offset translation
│   ├── page.py                      # Page object — frame slot holding rows from disk
│   └── replacers/
│       ├── replacer.py              # Abstract base class for all replacers
│       ├── lru_replacer.py          # Clock-approximation LRU
│       ├── fifo_replacer.py         # First-In First-Out eviction
│       └── two_list_replacer.py     # Hot/cold two-list (resists sequential scan flooding)
│
├── scheduler/
│   ├── scheduler.py                 # ThreadPoolScheduler — worker threads, query pipeline, stats
│   ├── fcfs.py                      # First-Come First-Served queue
│   ├── round_robin.py               # Per-client queues with rotating dispatch
│   └── priority.py                  # Short/high-priority queries promoted first
│
├── client/
│   ├── server.py                    # TCP server — accepts QUERY commands, routes to scheduler
│   └── client.py                    # TCP client — sends QUERY commands from CLI
│
├── data/
│   ├── loader.py                    # Parses weather.csv into 100-row pages
│   ├── index.py                     # Builds date → page_id index, range lookup
│   └── weather.csv                  # NOAA GSOD data, Bardufoss NO, 2018–2023
│
├── benchmark/
│   ├── runner.py                    # Internal benchmark — all 81 policy × algorithm combos
│   ├── runnerTCP.py                 # TCP benchmark — end-to-end response time measurement
│   ├── plots.py                     # Generates 6 matplotlib graphs from results.json
│   └── results/
│       ├── results.json             # Output from runner.py
│       └── plots/                   # Output PNG graphs from plots.py
│
├── test_fcfs.py                     # Smoke test — FCFS scheduler
├── test_round_robin.py              # Smoke test — Round Robin scheduler
└── test_priority.py                 # Smoke test — Priority scheduler
```

---

## File Descriptions

### Core

**`main.py`**  
CLI entry point. Accepts `--policy`, `--algorithm`, `--frames`, and `--clients` flags, wires all layers together, and runs a smoke-test batch of queries across the full 2018–2023 date range. Use this to test a single policy/algorithm combination interactively.

**`interfaces.py`**  
Defines the `Query` dataclass (start date, end date, client ID, priority) and the `Task` wrapper used by all three schedulers. `Task.__lt__` enables correct tiebreaking in the Priority scheduler's `PriorityQueue`.

### Buffer Layer

**`buffer/buffer_manager.py`**  
The brain of the system. Manages a fixed pool of `Page` frames in memory. Tracks which pages are loaded via `page_map` (page_id → frame index). On a cache miss, selects a victim frame via the replacer, evicts it, and loads the requested page from disk. Supports three interchangeable replacement algorithms via the `REPLACERS` registry and the `algorithm=` constructor argument.

**`buffer/disk_manager.py`**  
Handles all CSV I/O. `load_file()` partitions the CSV into 100-row pages stored in memory. `readPage(page_id, frame)` loads a page's rows into an existing frame in-place. `writePage` is a no-op since the weather dataset is read-only.

**`buffer/page.py`**  
Represents a single buffer frame. Tracks `index` (which page is loaded), `_pinned` (pin count for concurrent access), `dirty` flag, `state` (AVAILABLE / REFERENCED / PINNED for the LRU clock), and `data` (list of row dicts).

**`buffer/replacers/replacer.py`**  
Abstract base class enforcing `insert()`, `victim()`, `erase()`, and `__len__()` on all replacer implementations.

**`buffer/replacers/lru_replacer.py`**  
Clock-approximation LRU. Uses a circular scan over `frame_table` — referenced pages get one grace pass before becoming eligible for eviction. Best overall hit rate in benchmark results.

**`buffer/replacers/fifo_replacer.py`**  
Evicts the oldest page loaded into the buffer regardless of access frequency. Simple but vulnerable to sequential scan workloads. Lowest hit rate in benchmark results.

**`buffer/replacers/two_list_replacer.py`**  
Maintains a hot (active) list and cold (inactive) list. New pages enter the cold list; re-accessed pages are promoted to hot. Designed to resist cache flooding from large sequential scans. Performs between LRU and FIFO on the NOAA workload.

### Scheduler Layer

**`scheduler/scheduler.py`**  
`ThreadPoolScheduler` manages a fixed worker thread pool. Workers pull tasks from the scheduling policy queue and execute the query pipeline: date index lookup → buffer page fetch → row filtering → unpin. Tracks page hits, page faults, processed count, and average latency. Exposes `get_stats()` for the benchmark runner. Contains the `POLICIES` registry mapping CLI names to scheduler classes.

**`scheduler/fcfs.py`**  
Wraps `queue.Queue` for strict arrival-order processing. Lowest overhead, lowest average latency in benchmark results.

**`scheduler/round_robin.py`**  
Maintains a separate deque per client ID and rotates between active clients. Ensures no single client monopolises the workers under heavy concurrent load.

**`scheduler/priority.py`**  
Wraps `queue.PriorityQueue`. Shorter queries (by estimated date range) and lower priority numbers are served first. Good for latency-sensitive short queries at the cost of fairness to long queries.

### Client / TCP Layer

**`client/server.py`**  
TCP server listening on `127.0.0.1:8080`. Accepts `QUERY weather.csv WHERE date BETWEEN <start> AND <end>` commands. Each client connection is handled in its own thread. Configured with FCFS scheduling and LRU replacement — the combination that produced the best benchmark results. Pre-loads all pages into the buffer at startup for zero-fault first-query performance.

**`client/client.py`**  
TCP client. Connects to the server, sends a query string, and logs the response. Supports `--clients N` to spawn N concurrent threads from a single process, simulating multi-client load.

### Data Layer

**`data/loader.py`**  
Opens `weather.csv` and partitions rows into pages of 100 rows each using `csv.DictReader`. Returns a list of pages where each page is a list of row dicts.

**`data/index.py`**  
`adding_index()` builds a `{date_string: page_id}` dict from the loaded pages. `get_page_ids_for_range()` returns a sorted, deduplicated list of page IDs covering a given date range — used by the scheduler's query handler.

### Benchmark

**`benchmark/runner.py`**  
Internal benchmark runner. Tests all 81 combinations of 3 policies × 3 algorithms × 3 frame counts (4, 8, 12) × 3 client counts (2, 4, 8). Uses active polling to drain the query queue instead of fixed sleeps, keeping total runtime under 3 minutes. Writes results to `benchmark/results/results.json`.

**`benchmark/runnerTCP.py`**  
End-to-end TCP benchmark. Launches `main.py` as a subprocess for each of the 9 policy × algorithm combinations, fires a client query over the socket, and measures wall-clock response time. Demonstrates the full pipeline from network request to response.

**`benchmark/plots.py`**  
Reads `benchmark/results/results.json` and generates 6 matplotlib graphs saved to `benchmark/results/plots/`. Covers hit rate by algorithm and frame count, page faults, latency by policy and client count, concurrency effects, and a summary overview.

---

## Running the System

All commands should be run from the `src/` directory.

```bash
cd src
```

### 1. Single-run smoke test — `main.py`

Runs a batch of date-range queries with your chosen policy and algorithm and prints final stats.

```bash
python main.py --policy fcfs --algorithm lru --frames 32 --clients 4
```

**Flags:**

| Flag | Options | Default |
|---|---|---|
| `--policy` | `fcfs`, `rr`, `priority` | `fcfs` |
| `--algorithm` | `lru`, `fifo`, `two_list` | `lru` |
| `--frames` | integer | `32` |
| `--clients` | integer | `4` |

---

### 2. TCP server and client

Run the full network pipeline. Requires two terminal windows both opened to `src/`.

**Terminal 1 — start the server:**
```bash
python client/server.py
```
Expected output:
```
Loaded 22 pages, 2189 dates indexed
Server listening on 127.0.0.1:8080
```
The server runs indefinitely until you press `Ctrl+C`.

**Terminal 2 — send a query:**
```bash
python client/client.py --start 2020-01-01 --end 2020-06-30
```
Expected output:
```
2026-05-03 21:14:05,632 [INFO] [Thread-1] root: OK: OK query accepted: 2020-01-01 to 2020-06-30
```

**Send multiple concurrent clients:**
```bash
python client/client.py --start 2018-01-01 --end 2018-12-31 --clients 4
```
This spawns 4 threads simultaneously, simulating concurrent client load. Watch the server terminal to see the scheduler dispatching queries across worker threads.

**Query format the server accepts:**
```
QUERY weather.csv WHERE date BETWEEN <YYYY-MM-DD> AND <YYYY-MM-DD>
```
Valid dates are **2018-01-01** through **2023-12-31**.

---

### 3. Internal benchmark — `runner.py`

Tests all 81 policy × algorithm combinations automatically. Results go to `benchmark/results/results.json`.

```bash
python benchmark/runner.py
```

Expected runtime: **2–3 minutes** for all 81 runs.

Sample summary output:
```
── Summary: avg latency and hit rate by algorithm ──────────────────
  lru           avg_latency=  23.61 ms  avg_hit_rate= 26.5%
  fifo          avg_latency=  20.85 ms  avg_hit_rate= 17.9%
  two_list      avg_latency=  23.46 ms  avg_hit_rate= 21.5%
── Summary: avg latency by policy ──────────────────────────────────
  fcfs        avg_latency=  21.44 ms
  rr          avg_latency=  23.87 ms
  priority    avg_latency=  22.61 ms
```

---

### 4. Generate benchmark graphs — `plots.py`

Reads `benchmark/results/results.json` and writes 6 PNG graphs to `benchmark/results/plots/`.

```bash
python benchmark/plots.py
```

**Graphs produced:**

| File | What it shows |
|---|---|
| `plot1_hit_rate_by_algorithm_frames.png` | Buffer hit rate by algorithm across frame counts |
| `plot2_page_faults_by_algorithm_frames.png` | Page faults by algorithm across frame counts |
| `plot3_latency_by_policy_clients.png` | Query latency by scheduling policy across client counts |
| `plot4_hit_rate_by_algorithm_clients.png` | Hit rate by algorithm across concurrent client counts |
| `plot5_latency_by_algorithm_frames.png` | Latency by algorithm across frame counts |
| `plot6_summary_overview.png` | Side-by-side summary: overall hit rate and latency |

Run `runner.py` before `plots.py` — `plots.py` will exit with an error if `results.json` is not found.

---

### 5. TCP benchmark — `runnerTCP.py`

Measures end-to-end wall-clock response time across all 9 policy × algorithm combinations by launching the server as a subprocess and firing a real client query for each.

```bash
python benchmark/runnerTCP.py
```

Note: this runner uses `main.py` as the server subprocess and measures response time from the client's perspective. It requires no separate server process — `runnerTCP.py` manages server startup and shutdown automatically for each run.

---

### 6. Scheduler unit tests

Three standalone tests that verify each scheduling policy independently without the buffer or TCP layers.

```bash
python test_fcfs.py
python test_round_robin.py
python test_priority.py
```

---

## Scheduling Policies

| Policy | Description | Best for |
|---|---|---|
| `fcfs` | First-Come First-Served — strict arrival order | Lowest overhead, most predictable latency |
| `rr` | Round Robin — rotates between active clients | Fairness across many concurrent clients |
| `priority` | Short queries promoted, lower priority number served first | Latency-sensitive short queries |

---

## Page Replacement Algorithms

| Algorithm | Description | Benchmark result |
|---|---|---|
| `lru` | Evicts least recently used page (clock approximation) | Best hit rate — 26.5% avg, 36.1% at 12 frames |
| `fifo` | Evicts oldest loaded page regardless of access frequency | Lowest hit rate — 17.9% avg |
| `two_list` | Hot/cold lists — resists sequential scan flooding | Mid hit rate — 21.5% avg |

---

## Key Design Decisions

**LRU and FCFS hardcoded in `server.py`** — after benchmarking all 9 combinations, LRU produced the highest buffer hit rate and FCFS produced the lowest query latency. The production TCP server uses these as its fixed configuration.

**Active drain in `runner.py`** — the benchmark polls `scheduler._processed` every 100ms rather than sleeping a fixed duration, reducing total benchmark runtime from ~12 minutes to ~2–3 minutes.

**`REPLACERS` and `POLICIES` registries** — both `buffer_manager.py` and `scheduler.py` expose dicts mapping CLI string names to their classes. This lets `main.py`, `runner.py`, and tests select algorithms by name without importing individual classes.

**`Task.__lt__` tiebreaker** — `PriorityQueue` compares full tuples when two entries have equal priority. Without `__lt__` on `Task`, the priority scheduler crashes when two sentinel shutdown tasks have identical priority values. The tiebreaker uses `enqueued_at` to preserve arrival order within a priority level.

---

## Base Repository

This project extends [dbms-buffer-pool-manager-python](https://github.com/Naman-Bhalla/dbms-buffer-pool-manager-python) by Naman Bhalla, which provided the `Page`, `DiskManager` stub, and `Replacer` abstract base class with a base LRU implementation.

---

*ECE 402c — Operating System Design · Spring 2026*  
*Travis Potter · Ryan Brass · Andrew Kostick*
