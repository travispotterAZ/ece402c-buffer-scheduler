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
        _, _, _, task = self.task_q.get()
        return task

    def task_done(self):
        self.task_q.task_done()

    def qsize(self):
        return self.task_q.qsize()

    def empty(self):
        return self.task_q.empty()