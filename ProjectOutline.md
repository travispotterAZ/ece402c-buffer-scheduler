# ECE 402c — OS Buffer Management & Query Scheduler
### Simulated OS Buffer Manager applied to NOAA Weather Data Analysis
**Team:** Travis Potter · Ryan Brass · Andrew Kostick

---

## Overview

This project implements a simulated OS buffer manager and query scheduler in Python, applying core OS memory and I/O design principles to concurrent date-range queries over NOAA global weather records.

The system is built in four cooperating layers that mirror real OS components:

- **TCP Client Layer** — simulates processes issuing date-range queries
- **Process Scheduler** — delegates queries to worker threads via configurable scheduling policies
- **Paged Buffer Cache** — manages a fixed pool of memory frames using configurable replacement algorithms
- **File System Layer** — translates logical page addresses to physical byte offsets on disk

Built on top of [`dbms-buffer-pool-manager-python`](https://github.com/Naman-Bhalla/dbms-buffer-pool-manager-python) as a foundation, extended with additional replacement policies, a query scheduler, TCP networking, and NOAA data integration.

---

## Architecture

```
[ TCP Clients ]
      │  QUERY weather.csv WHERE date BETWEEN <start> AND <end>
      ▼
[ Process Scheduler ]
      │  FCFS / Round Robin / Priority
      ▼
[ Paged Buffer Cache ]
      │  FIFO / LRU / Two-List
      ▼
[ File System Layer ]
      │  (filename, page_id) → byte offset → disk read
      ▼
[ NOAA CSV on Disk ]
```

---

## Features

### Scheduling Policies
| Policy | Description |
|---|---|
| FCFS | First-come, first-served queue |
| Round Robin | Time-sliced dispatch across active queries |
| Priority | Short queries promoted; minimizes latency for high-priority clients |

### Page Replacement Algorithms
| Algorithm | Description |
|---|---|
| FIFO | Evicts the oldest page in the buffer |
| LRU | Evicts the least recently used page |
| Two-List | Hot/cold lists; resists cache flooding from large sequential scans |

### Additional Features
- Sub-range hit detection — identifies page IDs already in memory when queries overlap
- Date index — maps date ranges to page IDs for O(1) lookup
- Configurable frame pool size and number of concurrent clients
- Benchmark harness producing graphs across all policy/algorithm combinations

---

## Project Structure

```
.
├── buffer/
│   ├── page.py              # Page class (from base repo, extended)
│   ├── disk_manager.py      # Disk I/O and byte-offset translation
│   ├── buffer_manager.py    # Frame pool, pin/unpin, dirty tracking
│   └── replacers/
│       ├── replacer.py      # Abstract base class
│       ├── lru.py           # LRU (from base repo)
│       ├── fifo.py          # FIFO implementation
│       └── two_list.py      # Two-List (hot/cold) implementation
├── scheduler/
│   ├── scheduler.py         # Thread pool + task queue
│   ├── fcfs.py              # FCFS dispatch
│   ├── round_robin.py       # Round Robin dispatch
│   └── priority.py          # Priority dispatch
├── client/
│   ├── server.py            # TCP server socket
│   └── client.py            # TCP client — sends QUERY commands
├── data/
│   ├── loader.py            # NOAA CSV parser, 100-row pages
│   └── index.py             # Date → page_id index
├── benchmark/
│   ├── runner.py            # Runs all policy × algorithm combinations
│   └── plots.py             # Matplotlib graphs
├── interfaces.py            # Shared Query object and interface contracts
├── main.py                  # Entry point — CLI flags for policy and algorithm
└── README.md
```

---

## Getting Started

### Requirements
- Python 3.10+
- `matplotlib` (for benchmark graphs)

```bash
pip install matplotlib
```

### NOAA Data
Download a CSV from [NOAA Global Surface Summary of Day (GSOD)](https://www.ncei.noaa.gov/data/global-summary-of-the-day/) and place it at `data/weather.csv`. A single station across a few years is sufficient.

### Run the server
```bash
python main.py --policy fcfs --algorithm lru --frames 32
```

### Run a client query
```bash
python client/client.py --start 2020-01-01 --end 2020-06-30
```

### Run benchmarks
```bash
python benchmark/runner.py
```
Outputs graphs to `benchmark/results/`.

---

## CLI Flags

| Flag | Options | Default |
|---|---|---|
| `--policy` | `fcfs`, `rr`, `priority` | `fcfs` |
| `--algorithm` | `fifo`, `lru`, `two_list` | `lru` |
| `--frames` | integer | `32` |
| `--clients` | integer | `4` |

---

## Build Plan (4-Day Sprint)

| Day | Travis | Ryan | Andrew |
|---|---|---|---|
| 1 | FIFO replacer; Two-List skeleton | Thread pool + FCFS queue | NOAA CSV parsed, date index built |
| 2 | Two-List replacer + PagedFile + sub-range hit detection | Round Robin + Priority scheduling | TCP client/server end-to-end |
| 3 | Integration + smoke testing | Integration + smoke testing | Run 9 combos, collect data |
| 4 | Write up buffer/file system section | Write up scheduler + results analysis | Benchmark graphs + README |

---

## Experiments & Expected Results

The benchmark runner tests all combinations of scheduling policy and replacement algorithm, varying:
- Number of memory frames (e.g. 16, 32, 64)
- Number of concurrent clients (e.g. 2, 4, 8)
- Workload pattern (overlapping ranges vs. random lookups)

**Hypotheses:**
1. Two-List will outperform LRU under date-range scanning workloads — LRU is vulnerable to cache flooding when large scans evict frequently-used pages.
2. Priority scheduling minimizes latency for high-priority clients but increases wait time for low-priority ones; Round Robin distributes latency more evenly.
3. Overlapping date-range queries will produce lower page fault rates than random lookups, reflecting temporal locality when clients query similar time periods.

---

## Related Work

> Yuwei Huang and Guoliang Li. *Laser: Buffer-Aware Learned Query Scheduling in Master-Standby Databases.* PVLDB, 18(3): 743–755, 2024. doi:10.14778/3712221.3712239

Laser optimizes buffer utilization and query response time using learned models in master-standby databases. Our system evaluates different scheduling and replacement strategies experimentally rather than through learned models, making the tradeoffs directly observable.

---

## Base Repository

This project extends [dbms-buffer-pool-manager-python](https://github.com/Naman-Bhalla/dbms-buffer-pool-manager-python) by Naman Bhalla, which provides the `Page`, `DiskManager` stub, and `Replacer` abstract base class with an LRU implementation.

---

*ECE 402c — Operating System Design · Spring 2026*
