# Author: Ryan Brass
# Tests sample weather queries with FCFS scheduler

import time

from interfaces import Query
from scheduler.fcfs import FCFSScheduler
from scheduler.scheduler import ThreadPoolScheduler


def fake_query_handler(query, worker_id):
    """
    Fake handler for smoke testing.

    This avoids needing the real buffer manager, date index, or weather data.
    """
    print(
        f"[worker {worker_id}] handled query {query.query_id}: "
        f"{query.start_date} to {query.end_date}, "
        f"client={query.client_id}"
    )
    time.sleep(0.1)
    return []


def main():
    policy = FCFSScheduler(maxsize=500)

    scheduler = ThreadPoolScheduler(
        policy=policy,
        workers=2,
        queue_size=500,
        reject_when_full=False,
        query_handler=fake_query_handler
    )

    scheduler.start()

    queries = [
        Query("2020-01-01", "2020-01-31", client_id="client-A"),
        Query("2020-02-01", "2020-02-28", client_id="client-B"),
        Query("2020-03-01", "2020-03-31", client_id="client-C"),
        Query("2020-04-01", "2020-04-30", client_id="client-D"),
    ]

    for query in queries:
        accepted = scheduler.submit(query)

        if accepted:
            print(f"[main] submitted query {query.query_id}")
        else:
            print(f"[main] rejected query {query.query_id}")

    time.sleep(2)

    stats = scheduler.get_stats()
    print(f"[main] final stats: {stats}")

    scheduler.stop()


if __name__ == "__main__":
    main()