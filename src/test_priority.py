# Author: Ryan Brass
# Tests sample weather queries with priority scheduler

import time

from interfaces import Query
from scheduler.priority import PriorityScheduler
from scheduler.scheduler import ThreadPoolScheduler


def fake_query_handler(query, worker_id):
    """
    Fake handler for smoke testing.

    Priority should process shorter estimated query ranges first.
    If estimated sizes tie, lower priority number goes first.
    """
    print(
        f"[worker {worker_id}] handled query {query.query_id}: "
        f"client={query.client_id}, "
        f"estimated_size={query.estimated_size()}, "
        f"priority={query.priority}"
    )
    time.sleep(0.1)
    return []


def main():
    policy = PriorityScheduler(maxsize=500)

    scheduler = ThreadPoolScheduler(
        policy=policy,
        workers=1,
        queue_size=500,
        reject_when_full=False,
        query_handler=fake_query_handler
    )

    queries = [
        Query("2020-01-01", "2020-12-31", client_id="large-query", priority=5),
        Query("2020-01-01", "2020-01-07", client_id="small-query", priority=5),
        Query("2020-02-01", "2020-02-03", client_id="tiny-query", priority=5),
        Query("2020-03-01", "2020-03-10", client_id="medium-query", priority=1),
    ]

    for query in queries:
        accepted = scheduler.submit(query)

        if accepted:
            print(
                f"[main] submitted query {query.query_id}, "
                f"client={query.client_id}, "
                f"estimated_size={query.estimated_size()}, "
                f"priority={query.priority}"
            )
        else:
            print(f"[main] rejected query {query.query_id}")

    scheduler.start()

    time.sleep(2)

    stats = scheduler.get_stats()
    print(f"[main] final stats: {stats}")

    scheduler.stop()


if __name__ == "__main__":
    main()