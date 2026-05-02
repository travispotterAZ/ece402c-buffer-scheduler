# Author: Ryan Brass
# This file implements a round-robin scheduling policy rotating tasks between active client queues
from collections import defaultdict, deque
import queue
import threading
import time


class RoundRobinScheduler:
    """
    Round Robin scheduler across clients.

    Each client gets a queue.
    Scheduler rotates between active clients.
    """

    def __init__(self, maxsize: int = 0):
        self.maxsize = maxsize
        self.size = 0

        self.client_queues = defaultdict(deque)
        self.active_clients = deque()

        self.lock = threading.Lock()
        self.not_empty = threading.Condition(self.lock)

    def submit(self, task, block=True, timeout=None):
        """
        Add a task to the appropriate client queue.

        If the scheduler is full, this method either blocks until space becomes
        available, waits up to the provided timeout, or raises queue.Full.
        """
        deadline = None if timeout is None else time.time() + timeout

        with self.not_empty:
            while self.maxsize > 0 and self.size >= self.maxsize:
                if not block:
                    raise queue.Full

                if timeout is None:
                    self.not_empty.wait()
                else:
                    remaining = deadline - time.time()
                    if remaining <= 0:
                        raise queue.Full
                    self.not_empty.wait(remaining)

            if task.query is None:
                client_id = "__sentinel__"
            else:
                client_id = task.query.client_id

            was_empty = len(self.client_queues[client_id]) == 0

            self.client_queues[client_id].append(task)
            self.size += 1

            if was_empty:
                self.active_clients.append(client_id)

            self.not_empty.notify()

    def get_next(self):
        """
        Return the next task according to round-robin scheduling.

        The scheduler selects the next active client, removes one task from
        that client's queue, and then re-adds the client to the rotation if
        it still has pending work.
        """
        with self.not_empty:
            while not self.active_clients:
                self.not_empty.wait()

            client_id = self.active_clients.popleft()
            task = self.client_queues[client_id].popleft()
            self.size -= 1

            if self.client_queues[client_id]:
                self.active_clients.append(client_id)
            else:
                del self.client_queues[client_id]

            self.not_empty.notify()
            return task

    def task_done(self):
        """
        Compatibility method for the thread pool scheduler interface.
        """
        pass

    def qsize(self):
        """
        Return the total number of queued tasks across all clients.
        """
        with self.lock:
            return self.size

    def empty(self):
        """
        Return True if there are no queued tasks.
        """
        with self.lock:
            return self.size == 0