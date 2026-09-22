"""What changes between a laptop and a public host.

Everything here has a default that is right for the laptop, because that is
where this is usually run, and an environment variable that makes it right for
a machine with a public address. The defaults are the safe ones: the admin
surface is off, the limits are on.

One rule for the whole module: a setting is read at call time, never captured
at import. Tests move these, and a value frozen into a module-level constant
during collection cannot be moved back.
"""

from __future__ import annotations

import os
from pathlib import Path

ADMIN = "FRRF_ADMIN"
"""Whether the workshop and the notes page exist at all.

They start processes on the host and write files to it. On a laptop that is
the point; on a public address it is remote code execution with extra steps.
Off unless something says otherwise, and the routes are not registered rather
than merely refused, so there is nothing to find."""

DEV = "FRRF_DEV"
"""Whether /docs, /redoc and /openapi.json are served, and whether the Vite
dev server's origin is allowed through CORS."""

ORIGINS = "FRRF_CORS_ORIGINS"
MAX_VIDEO_SECONDS = "FRRF_MAX_VIDEO_SECONDS"
MAX_CONCURRENT = "FRRF_MAX_CONCURRENT_ANALYSES"
CACHE_BUDGET_GB = "FRRF_CACHE_BUDGET_GB"
RATE_PER_MINUTE = "FRRF_RATE_PER_MINUTE"
COOKIES_FILE = "FRRF_COOKIES_FILE"
BEHIND_PROXY = "FRRF_BEHIND_PROXY"
TRUSTED_HOSTS = "FRRF_TRUSTED_HOSTS"

DEV_ORIGINS = ("http://localhost:5173", "http://127.0.0.1:5173")
"""Vite's dev server. In production the frontend is served from this same
origin and CORS never comes up."""


def _flag(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _number(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        return default
    try:
        return float(raw)
    except ValueError as error:
        raise ValueError(f"{name} must be a number, not {raw!r}") from error


def admin() -> bool:
    return _flag(ADMIN, False)


def dev() -> bool:
    return _flag(DEV, False)


def behind_proxy() -> bool:
    return _flag(BEHIND_PROXY, False)


def cors_origins() -> list[str]:
    """Origins allowed to call the API cross-site.

    In production there are none: the built frontend is served from this same
    process, on this same origin. The list exists for the dev server and for
    anyone who chooses to split the two.
    """
    raw = os.environ.get(ORIGINS)
    if raw:
        return [origin.strip() for origin in raw.split(",") if origin.strip()]
    return list(DEV_ORIGINS) if dev() else []


def trusted_hosts() -> list[str] | None:
    raw = os.environ.get(TRUSTED_HOSTS)
    if not raw:
        return None
    return [host.strip() for host in raw.split(",") if host.strip()]


def max_video_seconds() -> float:
    """Longest video the fly will accept.

    A cap is not tidiness. decode() buffers the whole track as float32 at
    22,050 Hz, which is about 88 MB per hour before the copy that follows it,
    and nothing else in the request path bounds that. Twenty minutes is longer
    than any Rickroll and about 26 MB. Zero switches the cap off, which is
    reasonable on a laptop and is not reasonable anywhere else.
    """
    return _number(MAX_VIDEO_SECONDS, 1200.0)


def max_concurrent() -> int:
    """Analyses allowed to run at once.

    Each one holds a decoded track, a percept matrix and a yt-dlp download.
    Two vCPUs do not do four of these faster than they do two, they just do
    all four badly and hold four times the memory while failing.
    """
    return max(1, int(_number(MAX_CONCURRENT, 2)))


def cache_budget_bytes() -> int:
    """How much downloaded audio and video may sit in data/cache.

    Zero means no sweeping, which is the old behaviour and the reason a laptop
    accumulated 95 MB without anyone deciding to.
    """
    return int(_number(CACHE_BUDGET_GB, 5.0) * 1024**3)


def rate_per_minute() -> int:
    """Submissions allowed per client per minute. Zero switches it off."""
    return max(0, int(_number(RATE_PER_MINUTE, 10)))


def cookies_file() -> Path | None:
    """A Netscape-format cookie jar handed to yt-dlp, if there is one.

    Two different problems, one answer. Instagram returns an empty media
    response to anyone who is not logged in, so without this it does not work
    at all. And YouTube blocks datacenter address ranges -- which every host
    worth deploying on is -- so without this it stops working the moment it
    leaves a laptop.

    Mount it read-only and treat it as a credential, because it is one:
    whoever holds this file is logged in as that account. Use an account you
    are willing to lose.
    """
    raw = os.environ.get(COOKIES_FILE, "").strip()
    if not raw:
        return None
    path = Path(raw)
    return path if path.is_file() else None
