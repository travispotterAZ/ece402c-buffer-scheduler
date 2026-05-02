# Author: Ryan Brass
# Defines thread pool scheduler that manages processing of weather query tasks
import queue
import threading
import time
from typing import Callable, Optional

from interfaces import Query, Task


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
    ):
        # Storing scheduler configuration
        self.policy = policy
        self.workers = workers
        self.queue_size = queue_size
        self.reject_when_full = reject_when_full
        self.query_handler = query_handler

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
        self._start_time = time.time()

    def start(self) -> None:
        """
        Start worker threads and stats reporter.
        """

        # Creates and starts each worker thread
        for worker_id in range(self.workers):
            thread = threading.Thread(
                target=self._worker_loop,
                args=(worker_id,),
                daemon=True
            )
            thread.start()
            self._threads.append(thread)

        # Background thread for metrics
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

    def _default_query_handler(self, query: Query, worker_id: int) -> str:
        """
        Temporary placeholder query handler.

        Later, this should call:
        - date index
        - buffer manager
        - disk manager
        - result formatter
        """

        print(
            f"[worker {worker_id}] processing query {query.query_id}: "
            f"{query.start_date} to {query.end_date}"
        )

        time.sleep(0.25)

        print(f"[worker {worker_id}] finished query {query.query_id}")

        return "OK"

    def _stats_loop(self) -> None:
        """
        Periodically print scheduler statistics.
        """

        while not self._stop.is_set():
            time.sleep(2.0)

            with self._lock:
                processed = self._processed
                avg_ms = (
                    self._total_latency / processed * 1000.0
                    if processed
                    else 0.0
                )

            qlen = self.policy.qsize()
            elapsed = time.time() - self._start_time
            rps = processed / elapsed if elapsed > 0 else 0.0

            print(
                f"[stats] processed={processed} "
                f"avg_latency_ms={avg_ms:.2f} "
                f"qlen={qlen} "
                f"rps={rps:.2f}"
            )