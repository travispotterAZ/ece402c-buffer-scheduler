# Author: Ryan Brass
# Tests sample weather queries with round robin scheduler

import time

from interfaces import Query
from scheduler.round_robin import RoundRobinScheduler
from scheduler.scheduler import ThreadPoolScheduler


def fake_query_handler(query, worker_id):
    """
    Fake handler for smoke testing.

    Round robin should rotate between active clients instead of letting
    one client consume the entire queue first.
    """
    print(
        f"[worker {worker_id}] handled query {query.query_id}: "
        f"client={query.client_id}, "
        f"{query.start_date} to {query.end_date}"
    )
    time.sleep(0.1)
    return []


def main():
    policy = RoundRobinScheduler(maxsize=500)

    scheduler = ThreadPoolScheduler(
        policy=policy,
        workers=1,
        queue_size=500,
        reject_when_full=False,
        query_handler=fake_query_handler
    )

    queries = [
        Query("2020-01-01", "2020-01-05", client_id="A"),
        Query("2020-01-06", "2020-01-10", client_id="A"),
        Query("2020-01-11", "2020-01-15", client_id="A"),

        Query("2020-02-01", "2020-02-05", client_id="B"),
        Query("2020-02-06", "2020-02-10", client_id="B"),

        Query("2020-03-01", "2020-03-05", client_id="C"),
    ]

    for query in queries:
        accepted = scheduler.submit(query)

        if accepted:
            print(
                f"[main] submitted query {query.query_id} "
                f"from client {query.client_id}"
            )
        else:
            print(
                f"[main] rejected query {query.query_id} "
                f"from client {query.client_id}"
            )

    scheduler.start()

    time.sleep(2)

    stats = scheduler.get_stats()
    print(f"[main] final stats: {stats}")

    scheduler.stop()


if __name__ == "__main__":
    main()