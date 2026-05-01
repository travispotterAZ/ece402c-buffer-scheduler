import time

from interfaces import Query
from scheduler.round_robin import RoundRobinScheduler
from scheduler.scheduler import ThreadPoolScheduler


def main():
    policy = RoundRobinScheduler(maxsize=500)

    scheduler = ThreadPoolScheduler(
        policy=policy,
        workers=1,
        queue_size=500,
        reject_when_full=False
    )

    scheduler.start()

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

    time.sleep(5)
    scheduler.stop()


if __name__ == "__main__":
    main()