# Author: Ryan Brass
# Defines the shared Query and Task data structures used by the scheduler
from dataclasses import dataclass, field
from datetime import datetime
import itertools
import time
from typing import Optional


_query_counter = itertools.count()


@dataclass
class Query:
    """
    Represents one weather query.

    Example:
        Query("2020-01-01", "2020-06-30", client_id="client-A")
    """

    start_date: str
    end_date: str
    client_id: str = "unknown"
    priority: int = 5
    filename: str = "data/weather.csv"

    query_id: int = field(default_factory=lambda: next(_query_counter))
    created_at: datetime = field(default_factory=datetime.now)

    def estimated_size(self) -> int:
        """
        Estimate query size using date range length.
        Used by priority scheduling to promote shorter queries.
        """
        try:
            start = datetime.fromisoformat(self.start_date)
            end = datetime.fromisoformat(self.end_date)
            return max((end - start).days, 1)
        except ValueError:
            return 999999


@dataclass
class Task:
    """
    Wrapper around a Query.

    This is similar to the Task object from the earlier threaded server assignment.
    The scheduler processes Tasks, and each Task contains one Query.
    """

    query: Optional[Query]
    enqueued_at: float = field(default_factory=time.time)

    def __lt__(self, other: "Task") -> bool:
        """
        Tiebreaker for PriorityQueue when two tasks have equal priority tuples.
        Earlier-enqueued tasks win, which preserves arrival order within a
        priority level and prevents Task vs Task comparison crashes.
        """
        return self.enqueued_at < other.enqueued_at