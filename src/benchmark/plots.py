# Author: Travis Potter
# Generates benchmark graphs from results.json produced by runner.py
#
# Usage (from src/):
#   python benchmark/plots.py
#
# Reads benchmark/results/results.json and writes 6 plots to benchmark/results/plots/

import json
import os
import sys

import matplotlib.pyplot as plt
import numpy as np

# ── Paths ─────────────────────────────────────────────────────────────────────

RESULTS_FILE = os.path.join(os.path.dirname(__file__), "results", "results.json")
OUT_DIR      = os.path.join(os.path.dirname(__file__), "results", "plots")

# ── Constants ─────────────────────────────────────────────────────────────────

ALGORITHMS = ['lru', 'fifo', 'two_list']
POLICIES   = ['fcfs', 'rr', 'priority']
FRAMES     = [4, 8, 12]
CLIENTS    = [2, 4, 8]

ALG_LABELS = {'lru': 'LRU', 'fifo': 'FIFO', 'two_list': 'Two-List'}
POL_LABELS = {'fcfs': 'FCFS', 'rr': 'Round Robin', 'priority': 'Priority'}
ALG_COLORS = {'lru': '#1f77b4', 'fifo': '#d62728', 'two_list': '#2ca02c'}
POL_COLORS = {'fcfs': '#9467bd', 'rr': '#8c564b', 'priority': '#e377c2'}


# ── Helpers ───────────────────────────────────────────────────────────────────

def avg(records, key):
    return sum(r[key] for r in records) / len(records) if records else 0


def label_bars(ax, bars, fmt='{:.1f}', pad=0.2):
    for bar in bars:
        v = bar.get_height()
        ax.text(bar.get_x() + bar.get_width() / 2, v + pad,
                fmt.format(v), ha='center', va='bottom', fontsize=8)


# ── Plot functions ────────────────────────────────────────────────────────────

def plot1_hit_rate_by_algorithm_frames(data, out):
    """Hit rate by replacement algorithm and frame count — grouped bar chart."""
    fig, ax = plt.subplots(figsize=(8, 5))
    x     = np.arange(len(FRAMES))
    width = 0.25

    for i, alg in enumerate(ALGORITHMS):
        vals = [avg([r for r in data if r['algorithm'] == alg and r['frames'] == f], 'hit_rate')
                for f in FRAMES]
        bars = ax.bar(x + i * width, vals, width, label=ALG_LABELS[alg],
                      color=ALG_COLORS[alg], edgecolor='white', linewidth=0.5)
        label_bars(ax, bars, fmt='{:.1f}%')

    ax.set_xlabel('Buffer Frame Count')
    ax.set_ylabel('Average Buffer Hit Rate (%)')
    ax.set_title('Buffer Hit Rate by Replacement Algorithm and Frame Count')
    ax.set_xticks(x + width)
    ax.set_xticklabels([str(f) for f in FRAMES])
    ax.legend()
    ax.set_ylim(0, 50)
    ax.grid(axis='y', alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(out, 'plot1_hit_rate_by_algorithm_frames.png'), dpi=150)
    plt.close()
    print('[plots] plot1 — hit rate by algorithm x frames')


def plot2_page_faults_by_algorithm_frames(data, out):
    """Page faults by replacement algorithm and frame count — line chart."""
    fig, ax = plt.subplots(figsize=(8, 5))

    for alg in ALGORITHMS:
        vals = [avg([r for r in data if r['algorithm'] == alg and r['frames'] == f], 'page_faults')
                for f in FRAMES]
        ax.plot(FRAMES, vals, marker='o', label=ALG_LABELS[alg],
                color=ALG_COLORS[alg], linewidth=2, markersize=7)
        for f, v in zip(FRAMES, vals):
            ax.text(f, v + 0.5, f'{v:.1f}', ha='center', fontsize=8)

    ax.set_xlabel('Buffer Frame Count')
    ax.set_ylabel('Average Page Faults per Run')
    ax.set_title('Page Faults by Replacement Algorithm and Frame Count')
    ax.legend()
    ax.set_xticks(FRAMES)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(out, 'plot2_page_faults_by_algorithm_frames.png'), dpi=150)
    plt.close()
    print('[plots] plot2 — page faults by algorithm x frames')


def plot3_latency_by_policy_clients(data, out):
    """Query latency by scheduling policy and client count — grouped bar chart."""
    fig, ax = plt.subplots(figsize=(8, 5))
    x     = np.arange(len(CLIENTS))
    width = 0.25

    for i, pol in enumerate(POLICIES):
        vals = [avg([r for r in data if r['policy'] == pol and r['clients'] == c], 'avg_latency_ms')
                for c in CLIENTS]
        bars = ax.bar(x + i * width, vals, width, label=POL_LABELS[pol],
                      color=POL_COLORS[pol], edgecolor='white', linewidth=0.5)
        label_bars(ax, bars, fmt='{:.1f}')

    ax.set_xlabel('Number of Concurrent Clients')
    ax.set_ylabel('Average Query Latency (ms)')
    ax.set_title('Query Latency by Scheduling Policy and Client Count')
    ax.set_xticks(x + width)
    ax.set_xticklabels([str(c) for c in CLIENTS])
    ax.legend()
    ax.set_ylim(0, 35)
    ax.grid(axis='y', alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(out, 'plot3_latency_by_policy_clients.png'), dpi=150)
    plt.close()
    print('[plots] plot3 — latency by policy x clients')


def plot4_hit_rate_by_algorithm_clients(data, out):
    """Hit rate by replacement algorithm and client count — grouped bar chart."""
    fig, ax = plt.subplots(figsize=(8, 5))
    x     = np.arange(len(CLIENTS))
    width = 0.25

    for i, alg in enumerate(ALGORITHMS):
        vals = [avg([r for r in data if r['algorithm'] == alg and r['clients'] == c], 'hit_rate')
                for c in CLIENTS]
        bars = ax.bar(x + i * width, vals, width, label=ALG_LABELS[alg],
                      color=ALG_COLORS[alg], edgecolor='white', linewidth=0.5)
        label_bars(ax, bars, fmt='{:.1f}%')

    ax.set_xlabel('Number of Concurrent Clients')
    ax.set_ylabel('Average Buffer Hit Rate (%)')
    ax.set_title('Buffer Hit Rate by Replacement Algorithm and Client Count')
    ax.set_xticks(x + width)
    ax.set_xticklabels([str(c) for c in CLIENTS])
    ax.legend()
    ax.set_ylim(0, 40)
    ax.grid(axis='y', alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(out, 'plot4_hit_rate_by_algorithm_clients.png'), dpi=150)
    plt.close()
    print('[plots] plot4 — hit rate by algorithm x clients')


def plot5_latency_by_algorithm_frames(data, out):
    """Query latency by replacement algorithm and frame count — line chart."""
    fig, ax = plt.subplots(figsize=(8, 5))

    for alg in ALGORITHMS:
        vals = [avg([r for r in data if r['algorithm'] == alg and r['frames'] == f], 'avg_latency_ms')
                for f in FRAMES]
        ax.plot(FRAMES, vals, marker='s', label=ALG_LABELS[alg],
                color=ALG_COLORS[alg], linewidth=2, markersize=7)
        for f, v in zip(FRAMES, vals):
            ax.text(f, v + 0.3, f'{v:.1f}', ha='center', fontsize=8)

    ax.set_xlabel('Buffer Frame Count')
    ax.set_ylabel('Average Query Latency (ms)')
    ax.set_title('Query Latency by Replacement Algorithm and Frame Count')
    ax.legend()
    ax.set_xticks(FRAMES)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(out, 'plot5_latency_by_algorithm_frames.png'), dpi=150)
    plt.close()
    print('[plots] plot5 — latency by algorithm x frames')


def plot6_summary_overview(data, out):
    """Summary overview — overall hit rate by algorithm and latency by policy."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

    # Left: avg hit rate per algorithm
    alg_hits = [avg([r for r in data if r['algorithm'] == alg], 'hit_rate')
                for alg in ALGORITHMS]
    bars = ax1.bar([ALG_LABELS[a] for a in ALGORITHMS], alg_hits,
                   color=[ALG_COLORS[a] for a in ALGORITHMS], edgecolor='white')
    for bar, v in zip(bars, alg_hits):
        ax1.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.2,
                 f'{v:.1f}%', ha='center', va='bottom', fontsize=10, fontweight='bold')
    ax1.set_ylabel('Average Buffer Hit Rate (%)')
    ax1.set_title('Overall Hit Rate by Algorithm')
    ax1.set_ylim(0, 40)
    ax1.grid(axis='y', alpha=0.3)

    # Right: avg latency per policy
    pol_lat = [avg([r for r in data if r['policy'] == pol], 'avg_latency_ms')
               for pol in POLICIES]
    bars = ax2.bar([POL_LABELS[p] for p in POLICIES], pol_lat,
                   color=[POL_COLORS[p] for p in POLICIES], edgecolor='white')
    for bar, v in zip(bars, pol_lat):
        ax2.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.1,
                 f'{v:.1f} ms', ha='center', va='bottom', fontsize=10, fontweight='bold')
    ax2.set_ylabel('Average Query Latency (ms)')
    ax2.set_title('Overall Latency by Scheduling Policy')
    ax2.set_ylim(0, 32)
    ax2.grid(axis='y', alpha=0.3)

    fig.suptitle('ECE 402c — Buffer Manager & Scheduler Benchmark Summary',
                 fontsize=13, fontweight='bold')
    fig.tight_layout()
    fig.savefig(os.path.join(out, 'plot6_summary_overview.png'), dpi=150)
    plt.close()
    print('[plots] plot6 — summary overview')


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    if not os.path.exists(RESULTS_FILE):
        print(f'[plots] ERROR: results file not found at {RESULTS_FILE}')
        print('[plots] Run benchmark/runner.py first to generate results.')
        sys.exit(1)

    with open(RESULTS_FILE) as f:
        data = json.load(f)

    print(f'[plots] loaded {len(data)} results from {RESULTS_FILE}')
    os.makedirs(OUT_DIR, exist_ok=True)

    plot1_hit_rate_by_algorithm_frames(data, OUT_DIR)
    plot2_page_faults_by_algorithm_frames(data, OUT_DIR)
    plot3_latency_by_policy_clients(data, OUT_DIR)
    plot4_hit_rate_by_algorithm_clients(data, OUT_DIR)
    plot5_latency_by_algorithm_frames(data, OUT_DIR)
    plot6_summary_overview(data, OUT_DIR)

    print(f'\n[plots] all plots saved to {OUT_DIR}')


if __name__ == '__main__':
    main()