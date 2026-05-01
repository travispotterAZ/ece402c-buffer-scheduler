import queue


class FCFSScheduler:
    """
    First-Come, First-Served scheduling policy.

    Tasks are processed in the order they arrive.
    """

    def __init__(self, maxsize: int = 0):
        self.task_q = queue.Queue(maxsize=maxsize)

    def submit(self, task, block=True, timeout=None):
        self.task_q.put(task, block=block, timeout=timeout)

    def get_next(self):
        return self.task_q.get()

    def task_done(self):
        self.task_q.task_done()

    def qsize(self):
        return self.task_q.qsize()

    def empty(self):
        return self.task_q.empty()