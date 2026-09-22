"""Keeping data/cache from becoming the whole disk.

Every analysis leaves an audio file and usually a video file behind, and
nothing ever removed them. That is right on a laptop for about a month and
wrong on a host with a public address immediately: the directory is an
allocation any caller can drive, one video at a time, until the disk is full.

Oldest first, by modification time, down to a budget. A cache is allowed to
lose things -- that is what makes it a cache. The one thing it may not lose is
a file some live job is still serving, so those are named and skipped.
"""

from __future__ import annotations

from pathlib import Path


def sweep(directory: Path, budget_bytes: int, keep: set[Path] | None = None) -> int:
    """Delete the oldest files until the directory fits. Returns bytes freed."""
    if budget_bytes <= 0 or not directory.is_dir():
        return 0

    protected = {path.resolve() for path in (keep or set())}
    files = []
    total = 0
    for path in directory.iterdir():
        if not path.is_file() or path.name == ".gitkeep":
            continue
        try:
            size = path.stat().st_size
            files.append((path.stat().st_mtime, size, path))
            total += size
        except OSError:
            continue

    if total <= budget_bytes:
        return 0

    freed = 0
    for _, size, path in sorted(files):
        if total - freed <= budget_bytes:
            break
        if path.resolve() in protected:
            continue
        try:
            path.unlink()
        except OSError:
            continue
        freed += size
    return freed
