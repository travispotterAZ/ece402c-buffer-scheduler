# Author: Ryan Brass
#
# Co-Author: Travis Potter
#
# Defines thread pool scheduler that manages processing of weather query tasks
import queue
import threading
import time
from datetime import datetime
from typing import Callable, Optional

from interfaces import Query, Task
from scheduler.fcfs import FCFSScheduler
from scheduler.priority import PriorityScheduler
from scheduler.round_robin import RoundRobinScheduler
from data.index import get_page_ids_for_range


POLICIES = {
    "fcfs":     FCFSScheduler,
    "rr":       RoundRobinScheduler,
    "priority": PriorityScheduler,
}


class ThreadPoolScheduler:
    """
    Thread pool scheduler for weather queries.

    This class is similar to the earlier threaded pool assignment:
    - has fixed number of workers
    - has bounded queue through the scheduling policy
    - has stop event
    - tracks processed count and average latency
    - worker threads repeatedly pull tasks and process them
    """

    def __init__(
        self,
        policy,
        workers: int = 4,
        queue_size: int = 500,
        reject_when_full: bool = False,
        query_handler: Optional[Callable[[Query, int], str]] = None,
        buffer_manager=None,
        date_index: Optional[dict] = None,
    ):
        # Storing scheduler configuration
        self.policy = policy
        self.workers = workers
        self.queue_size = queue_size
        self.reject_when_full = reject_when_full
        self.query_handler = query_handler

        # Buffer manager and date index used by the real query handler
        self.buffer_manager = buffer_manager
        self.date_index = date_index

        # Event used to coordinate shutdown across worker and stats threads.
        self._stop = threading.Event()

        # Track worker thread objects so they can be joined during shutdown.
        self._threads: list[threading.Thread] = []

        # Separate background thread for periodically reporting scheduler stats.
        self._stats_thread: Optional[threading.Thread] = None

        # Lock protects shared scheduler metrics from concurrent updates.
        self._lock = threading.Lock()

        # Runtime metrics used by the stats reporter.
        self._processed = 0
        self._total_latency = 0.0
        self._page_faults = 0
        self._page_hits = 0
        self._start_time = time.time()

    def start(self) -> None:
        """
        Start worker threads and stats reporter.
        """
        for worker_id in range(self.workers):
            thread = threading.Thread(
                target=self._worker_loop,
                args=(worker_id,),
                daemon=True
            )
            thread.start()
            self._threads.append(thread)

        self._stats_thread = threading.Thread(
            target=self._stats_loop,
            daemon=True
        )
        self._stats_thread.start()

    def stop(self) -> None:
        """
        Signal worker threads to stop.

        Sends sentinel tasks to wake workers that may be blocked waiting
        for work.
        """
        self._stop.set()

        for _ in range(self.workers):
            try:
                self.policy.submit(Task(query=None), block=False)
            except queue.Full:
                pass

        for thread in self._threads:
            thread.join(timeout=2.0)

        if self._stats_thread:
            self._stats_thread.join(timeout=2.0)

    def submit(self, query: Query) -> bool:
        """
        Submit a Query to the scheduler.

        Returns True if the query was accepted.
        Returns False if the queue was full and reject_when_full=True.
        """
        task = Task(query=query)

        try:
            if self.reject_when_full:
                self.policy.submit(task, block=False)
            else:
                self.policy.submit(task, block=True, timeout=1.0)

            return True

        except queue.Full:
            return False

    def get_stats(self) -> dict:
        """
        Return a snapshot of current scheduler metrics.
        Used by the benchmark runner to collect results.
        """
        with self._lock:
            processed = self._processed
            total_latency = self._total_latency
            page_faults = self._page_faults
            page_hits = self._page_hits

        elapsed = time.time() - self._start_time
        return {
            "processed":       processed,
            "avg_latency_ms":  (total_latency / processed * 1000.0) if processed else 0.0,
            "rps":             processed / elapsed if elapsed > 0 else 0.0,
            "page_faults":     page_faults,
            "page_hits":       page_hits,
            "elapsed_s":       elapsed,
        }

    def _worker_loop(self, worker_id: int) -> None:
        """
        Worker threads repeatedly pull tasks from the selected scheduling policy.
        """
        while not self._stop.is_set():
            task = self.policy.get_next()

            if task.query is None:
                self.policy.task_done()
                break

            started = time.time()

            try:
                if self.query_handler is not None:
                    self.query_handler(task.query, worker_id)
                else:
                    self._default_query_handler(task.query, worker_id)

            except Exception as e:
                print(f"[worker {worker_id}] error while processing query: {e}")

            finished = time.time()

            with self._lock:
                self._processed += 1
                self._total_latency += finished - task.enqueued_at

            self.policy.task_done()

    def _default_query_handler(self, query: Query, worker_id: int) -> list:
        """
        Real query handler — ties together the date index, buffer manager,
        and page data to answer a date-range weather query.

        Pipeline:
            1. Look up which page IDs cover the requested date range
            2. Check which pages are already in the buffer (hits) vs need loading (faults)
            3. Fetch each page through the buffer manager (handles eviction automatically)
            4. Filter rows to only those within [start_date, end_date]
            5. Unpin each page once its rows have been read
        """
        print(
            f"[worker {worker_id}] processing query {query.query_id}: "
            f"{query.start_date} to {query.end_date}"
        )

        if self.buffer_manager is None or self.date_index is None:
            print(f"[worker {worker_id}] buffer_manager or date_index not set — skipping")
            return []

        start = datetime.fromisoformat(query.start_date)
        end   = datetime.fromisoformat(query.end_date)

        page_ids = get_page_ids_for_range(self.date_index, query.start_date, query.end_date)

        results = []
        fetched_page_ids = []

        for page_id in page_ids:

            # Sub-range hit detection — check if already in buffer before fetching
            if page_id in self.buffer_manager.page_map:
                with self._lock:
                    self._page_hits += 1
            else:
                with self._lock:
                    self._page_faults += 1

            page = self.buffer_manager.fetchPage(page_id)

            if page is None:
                print(f"[worker {worker_id}] could not fetch page {page_id} — all frames pinned")
                continue

            fetched_page_ids.append(page_id)

            # Filter rows within the exact date range
            for row in page.data:
                try:
                    row_date = datetime.fromisoformat(row["DATE"])
                    if start <= row_date <= end:
                        results.append(row)
                except (KeyError, ValueError):
                    continue

        # Unpin all pages now that we are done reading them
        for page_id in fetched_page_ids:
            self.buffer_manager.unpinPage(page_id, is_dirty=False)

        print(
            f"[worker {worker_id}] finished query {query.query_id} — "
            f"{len(results)} rows from {len(fetched_page_ids)} pages"
        )

        return results

    def _stats_loop(self) -> None:
        """
        Periodically print scheduler statistics.
        """
        while not self._stop.is_set():
            time.sleep(2.0)

            stats = self.get_stats()

            print(
                f"[stats] processed={stats['processed']} "
                f"avg_latency_ms={stats['avg_latency_ms']:.2f} "
                f"rps={stats['rps']:.2f} "
                f"page_hits={stats['page_hits']} "
                f"page_faults={stats['page_faults']}"
            )