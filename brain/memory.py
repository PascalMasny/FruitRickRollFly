"""How much RAM the fly may use, and how that ceiling becomes a block size.

Nothing in this circuit needs a large working set. What it does need is care
with one expression. ``projection[:, claws]`` in :meth:`KenyonCells.drive` is
the gather that collects each Kenyon cell's claws, and NumPy materialises the
whole ``(percepts, n_kenyon, n_claws)`` result before anything is summed. At
the default wiring that is 320 kB *per percept*, so the threshold calibration,
which samples 20,000 percepts, asked for 6.4 GB in a single temporary. Every
fold asked again. A 16 GB machine swapped.

The fix is to gather in row blocks. The sum runs along the claw axis, so
splitting the rows changes no arithmetic whatsoever: blocked and unblocked
drives are bit-identical, and the blocked one is about 30 percent faster
besides, because a 655 MB temporary fits in no cache anyone sells.

This module owns the ceiling and the arithmetic that keeps the blocks under
it. The ceiling is meant as a real limit rather than a hint: ``frrf-train``
projects its footprint against it before starting and reports the measured
peak against it at the end.
"""

from __future__ import annotations

import os

DEFAULT_BUDGET_GB = 8.0
"""Gigabytes of working set training is allowed. Eight leaves room for the rest
of a 16 GB machine; the circuit itself wants well under one."""

BUDGET_ENV = "FRRF_MEMORY_BUDGET_GB"
"""Environment override, so the limit can be set without touching a CLI."""

WORKING_SHARE = 0.25
"""Fraction of the budget any single blocked temporary may claim.

A quarter, because the blocked loops are not the only thing alive while they
run: the corpus, the Kenyon tags and the fold's own copies are all resident,
and a temporary that took the whole budget would leave nothing for them.
"""

ALLOCATOR_HEADROOM = 2.0
"""Multiplier on the arrays a projection can name, to cover the ones it cannot.

NumPy releases its temporaries promptly; the allocator underneath does not
always hand the pages straight back, and every fold leaves a 0.30 GB
calibration buffer behind it for a while. On the 65-track corpus the named
arrays came to 0.73 GB while the kernel reported a 1.21 GB peak, a factor of
1.7. Two is that rounded up, and it is frankly a fudge factor: it is here so
that the check errs towards refusing a run that would swap, which is the
failure this module exists to prevent.
"""

GB = 1024**3


def _from_env() -> float:
    raw = os.environ.get(BUDGET_ENV)
    if raw is None:
        return DEFAULT_BUDGET_GB
    try:
        value = float(raw)
    except ValueError as exc:
        raise ValueError(f"{BUDGET_ENV} must be a number of gigabytes, not {raw!r}") from exc
    if value <= 0:
        raise ValueError(f"{BUDGET_ENV} must be positive, not {value}")
    return value


_budget_gb: float | None = None


def budget_gb() -> float:
    """The current ceiling, in gigabytes. Read at call time, never cached by
    importers, so ``--memory-budget`` still reaches code imported before it."""
    global _budget_gb
    if _budget_gb is None:
        _budget_gb = _from_env()
    return _budget_gb


def budget_bytes() -> int:
    return int(budget_gb() * GB)


def set_budget(gb: float) -> None:
    """Move the ceiling. Called by ``frrf-train --memory-budget``."""
    global _budget_gb
    if gb <= 0:
        raise ValueError(f"memory budget must be positive, not {gb}")
    _budget_gb = float(gb)


def block_rows(bytes_per_row: int, prefer: int) -> int:
    """How many rows a blocked loop may take at once.

    ``prefer`` is the block size chosen on speed grounds; this returns it
    unchanged unless the budget cannot afford that many rows, and never
    returns less than one, because a loop that processes no rows is worse
    than one that briefly exceeds its budget.
    """
    affordable = int(budget_bytes() * WORKING_SHARE) // max(int(bytes_per_row), 1)
    return max(1, min(int(prefer), affordable))


def fits(bytes_needed: int) -> bool:
    return bytes_needed <= budget_bytes()


def human(bytes_count: float) -> str:
    """Bytes as the GB figure a memory limit is argued about in."""
    return f"{bytes_count / GB:.2f} GB"


def peak_rss_bytes() -> int:
    """High-water mark of this process's resident set.

    ``ru_maxrss`` is bytes on macOS and kilobytes on Linux. That difference is
    documented rather than guessable, so it is branched on explicitly; getting
    it wrong reports a limit as kept by a factor of a thousand.
    """
    import resource
    import sys

    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return int(peak) if sys.platform == "darwin" else int(peak) * 1024
