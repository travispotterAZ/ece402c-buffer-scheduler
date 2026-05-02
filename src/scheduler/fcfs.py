# Author: Ryan Brass
# Implements FCFS scheduling policy, tasks processed in order they arrive
import queue


class FCFSScheduler:
    """
    First-Come, First-Served scheduling policy.

    Tasks are processed in the order they arrive.
    """

    def __init__(self, maxsize: int = 0):
        self.task_q = queue.Queue(maxsize=maxsize)

    def submit(self, task, block=True, timeout=None):
        """
        Submit a task to the queue.
        """
        self.task_q.put(task, block=block, timeout=timeout)

    def get_next(self):
        """
        Retrieve the next task in arrival order.
        """
        return self.task_q.get()

    def task_done(self):
        """
        Mark the most recently retrieved task as completed.
        """
        self.task_q.task_done()

    def qsize(self):
        """
        Return the current number of queued tasks.
        """
        return self.task_q.qsize()

    def empty(self):
        """
        Return True if there are no queued tasks.
        """
        return self.task_q.empty()