"""In-memory sliding-window rate limit (fine for a single process; use Redis in production)."""
import time
from collections import defaultdict, deque

from fastapi import HTTPException

_hits: dict[str, deque] = defaultdict(deque)


def limit(key: str, max_calls: int, window_s: int = 60) -> None:
    now = time.monotonic()
    q = _hits[key]
    while q and now - q[0] > window_s:
        q.popleft()
    if len(q) >= max_calls:
        raise HTTPException(429, "Too many requests. Please wait a moment and try again")
    q.append(now)
