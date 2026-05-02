# Author: Ryan Brass
# Implements a priority-based scheduling policy processing shorter, higher priority tasks first
import queue


class PriorityScheduler:
    """
    Priority scheduler.

    Sorting order:
        1. Shorter estimated query size first
        2. Lower priority number first
        3. Earlier query_id first
    """

    def __init__(self, maxsize: int = 0):
        self.task_q = queue.PriorityQueue(maxsize=maxsize)

    def submit(self, task, block=True, timeout=None):
        """
        Submit a task to the priority queue.
        """
        if task.query is None:
            priority_tuple = (float("inf"), float("inf"), float("inf"), task)
        else:
            query = task.query
            priority_tuple = (
                query.estimated_size(),
                query.priority,
                query.query_id,
                task
            )

        self.task_q.put(priority_tuple, block=block, timeout=timeout)

    def get_next(self):
        """
        Retrieve the next task according to priority order.
        """
        _, _, _, task = self.task_q.get()
        return task

    def task_done(self):
        """
        Mark the most recently retrieved task as completed.

        This keeps PriorityQueue's internal task tracking consistent.
        """
        self.task_q.task_done()

    def qsize(self):
        """
        Return the current number of queued tasks.
        """
        return self.task_q.qsize()

    def empty(self):
        """
        Return True if the priority queue currently has no tasks.
        """
        return self.task_q.empty()