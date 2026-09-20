"""The memory ceiling, and the blocking that keeps the calyx under it.

The gather in ``KenyonCells.drive`` once ran unblocked and asked for 6.4 GB in
a single temporary. These tests pin the two things that made the fix safe: the
blocking changes no arithmetic, and the budget actually reaches the loops.
"""

import numpy as np
import pytest

from brain import memory
from brain.config import BrainConfig
from brain.layers import AntennalLobe, KenyonCells, peak_working_bytes


@pytest.fixture
def budget():
    """Restore the process-wide ceiling, whatever a test did to it."""
    before = memory.budget_gb()
    yield memory.set_budget
    memory.set_budget(before)


@pytest.fixture
def projection(config):
    rng = np.random.default_rng(17)
    receptors = rng.random((900, config.n_receptors), dtype=np.float32)
    lobe = AntennalLobe(config)
    lobe.calibrate(receptors)
    return lobe.transform(receptors)


def test_blocking_changes_no_arithmetic(config, projection, budget):
    """The sum runs along the claw axis, so splitting rows must be exact.

    Not ``allclose``: any difference at all would mean the block size had
    become a parameter of the model, and the thresholds and the winners it
    feeds would drift with the machine the training ran on.
    """
    cells = KenyonCells(config)
    budget(64.0)
    whole = cells.drive(projection)
    budget(0.001)
    assert memory.block_rows(config.n_kenyon * config.n_claws * 4, 256) < 256
    assert np.array_equal(cells.drive(projection), whole)


def test_thresholds_and_winners_survive_a_tight_budget(config, projection, budget):
    budget(64.0)
    roomy = KenyonCells(config)
    roomy.calibrate(projection)
    winners = roomy.respond(projection)

    budget(0.001)
    cramped = KenyonCells(config)
    cramped.calibrate(projection)
    assert np.array_equal(cramped.thresholds, roomy.thresholds)
    assert np.array_equal(cramped.respond(projection), winners)


def test_a_tighter_budget_buys_smaller_blocks(budget):
    budget(8.0)
    roomy = memory.block_rows(bytes_per_row=1_000_000, prefer=100_000)
    budget(1.0)
    assert memory.block_rows(bytes_per_row=1_000_000, prefer=100_000) < roomy


def test_a_block_never_shrinks_below_one_row(budget):
    """A loop that processes no rows never terminates, which is worse than a
    loop that briefly overruns its budget."""
    budget(0.000001)
    assert memory.block_rows(bytes_per_row=10**9, prefer=4096) == 1


def test_the_projection_stays_under_the_ceiling(config, budget):
    budget(8.0)
    assert sum(peak_working_bytes(config, percepts=100_000).values()) < memory.budget_bytes()


def test_the_default_wiring_is_projected_honestly():
    """The numbers the CLI prints are for the fly that actually ships."""
    terms = peak_working_bytes(BrainConfig(), percepts=66_035)
    # The gather was the whole problem; it must now be the smallest term.
    assert terms["claw gather block"] == min(terms.values())
    assert sum(terms.values()) < 1 * memory.GB


def test_the_budget_is_read_at_call_time(budget):
    budget(8.0)
    assert memory.budget_bytes() == int(8.0 * memory.GB)
    budget(2.0)
    assert memory.budget_bytes() == int(2.0 * memory.GB)


def test_a_nonsense_budget_is_refused(budget):
    with pytest.raises(ValueError):
        budget(0.0)
    with pytest.raises(ValueError):
        budget(-1.0)
