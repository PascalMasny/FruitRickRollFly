"""A per-client ceiling on the endpoints that cost something.

Submitting a link makes this server talk to YouTube, download a file and burn
a core for a second. Appending a correction writes to a file that never
shrinks. Neither should be available at whatever rate a script can manage.

This is a sliding window held in this process, which is the right size for one
uvicorn and the wrong size for two: replicas each get their own allowance.
When this grows a second process the window has to move to Redis, and the
shape here -- one sorted deque of timestamps per client -- is the shape a
Redis sorted set takes anyway.
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request

from api import settings

WINDOW_SECONDS = 60.0

_HITS: defaultdict[str, deque[float]] = defaultdict(deque)
_LOCK = threading.Lock()

MAX_TRACKED = 10_000
"""Clients remembered at once. The table is itself an allocation a caller can
drive, so it is swept whenever it grows past this."""


def client(request: Request) -> str:
    """Who is asking.

    Behind a reverse proxy every request arrives from the proxy, so the first
    hop of X-Forwarded-For is the client -- but only where a proxy is actually
    in front, because otherwise the header is whatever the caller typed and
    the limit becomes advisory.
    """
    if settings.behind_proxy():
        forwarded = request.headers.get("x-forwarded-for", "")
        first = forwarded.split(",")[0].strip()
        if first:
            return first
    return request.client.host if request.client else "unknown"


def _prune(now: float) -> None:
    for key in [k for k, hits in _HITS.items() if not hits or now - hits[-1] > WINDOW_SECONDS]:
        del _HITS[key]


def allow(key: str, limit: int, now: float | None = None) -> bool:
    """Whether this client may act, recording the attempt if so."""
    if limit <= 0:
        return True
    now = time.monotonic() if now is None else now
    with _LOCK:
        if len(_HITS) > MAX_TRACKED:
            _prune(now)
        hits = _HITS[key]
        while hits and now - hits[0] >= WINDOW_SECONDS:
            hits.popleft()
        if len(hits) >= limit:
            return False
        hits.append(now)
        return True


def limit(request: Request) -> None:
    """FastAPI dependency. Raises 429 when the client is over its allowance."""
    if not allow(client(request), settings.rate_per_minute()):
        raise HTTPException(
            status_code=429,
            detail="Too many requests. The fly is only one animal.",
            headers={"Retry-After": str(int(WINDOW_SECONDS))},
        )


def reset() -> None:
    """Forget every client. For tests, which must not inherit each other's."""
    with _LOCK:
        _HITS.clear()
