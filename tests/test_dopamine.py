"""The pool that turns a stream of percepts into one decision."""

import numpy as np
import pytest

from brain.config import BrainConfig
from brain.dopamine import DopamineTrace, prediction_error


def test_dopamine_splits_the_error_by_sign():
    release = prediction_error(np.array([0.0, 0.0]), np.array([1.0, -1.0]))
    assert release.pam[0] > 0 and release.ppl1[0] == 0
    assert release.ppl1[1] > 0 and release.pam[1] == 0


def test_no_error_releases_no_dopamine():
    release = prediction_error(np.array([1.0, -1.0]), np.array([1.0, -1.0]))
    assert release.magnitude == pytest.approx(0.0)


def test_weights_scale_the_release():
    plain = prediction_error(np.array([0.0]), np.array([1.0]))
    scaled = prediction_error(np.array([0.0]), np.array([1.0]), np.array([3.0]))
    assert scaled.pam[0] == pytest.approx(3.0 * plain.pam[0])


@pytest.fixture
def config():
    return BrainConfig(da_tau=1.0, da_baseline=0.5, da_slope=0.15, da_commit=0.4)


def test_sustained_evidence_charges_the_pool_and_commits(config):
    trace = DopamineTrace(config)
    times = np.arange(1, 60) * config.window_hop_seconds
    dopamine, _ = trace.run(np.full(len(times), 0.95), times)
    assert dopamine[-1] > config.da_commit
    assert trace.committed_at is not None


def test_evidence_below_the_baseline_never_commits(config):
    trace = DopamineTrace(config)
    times = np.arange(1, 400) * config.window_hop_seconds
    dopamine, _ = trace.run(np.full(len(times), 0.2), times)
    assert trace.committed_at is None
    assert dopamine.max() == pytest.approx(0.0)


def test_a_lucky_second_in_a_long_track_is_not_enough(config):
    """The failure the tonic baseline exists to prevent."""
    times = np.arange(1, 3000) * config.window_hop_seconds
    rng = np.random.default_rng(0)
    evidence = np.where(rng.random(len(times)) < 0.05, 0.99, 0.1)
    trace = DopamineTrace(config)
    trace.run(evidence, times)
    assert trace.committed_at is None


def test_the_pool_drains_once_the_evidence_stops(config):
    times = np.arange(1, 200) * config.window_hop_seconds
    evidence = np.where(times < 5.0, 0.95, 0.0)
    trace = DopamineTrace(config)
    dopamine, _ = trace.run(evidence, times)
    assert dopamine.max() > config.da_commit
    assert dopamine[-1] < 0.01


def test_neither_pool_goes_negative(config):
    times = np.arange(1, 100) * config.window_hop_seconds
    trace = DopamineTrace(config)
    dopamine, aversion = trace.run(np.full(len(times), -1.0), times)
    assert dopamine.min() >= 0.0
    assert aversion.min() >= 0.0


def test_strong_dislike_fills_the_aversion_pool(config):
    times = np.arange(1, 100) * config.window_hop_seconds
    _, aversion = DopamineTrace(config).run(np.full(len(times), -0.95), times)
    assert aversion[-1] > config.da_commit


def test_the_commit_time_is_the_first_crossing(config):
    times = np.arange(1, 200) * config.window_hop_seconds
    trace = DopamineTrace(config)
    dopamine, _ = trace.run(np.full(len(times), 0.95), times)
    first = int(np.flatnonzero(dopamine >= config.da_commit)[0])
    assert trace.committed_at == pytest.approx(times[first])


def test_a_shorter_time_constant_commits_sooner(config):
    times = np.arange(1, 400) * config.window_hop_seconds
    evidence = np.full(len(times), 0.9)
    quick = DopamineTrace(BrainConfig(**{**config.to_dict(), "da_tau": 0.3}))
    slow = DopamineTrace(BrainConfig(**{**config.to_dict(), "da_tau": 3.0}))
    quick.run(evidence, times)
    slow.run(evidence, times)
    assert quick.committed_at < slow.committed_at


# ── the fast path: short memes ───────────────────────────────────────────────


@pytest.fixture
def slow(config):
    """A fly whose pool cannot commit inside a few seconds.

    The default commit threshold is 0.35, which a confident percept reaches in
    under a second, and a test of the fast path that the slow path wins is not
    a test of the fast path. These are the shipped tau and baseline with the
    threshold put out of reach, so only the burst can fire.
    """
    from dataclasses import replace

    return replace(config, da_tau=2.0, da_baseline=0.72, da_commit=0.85)


def _timeline(config, seconds: float, confidence: float):
    """A stretch of constant confidence, sampled at the listening hop."""
    hop = config.window_hop_seconds
    t = np.arange(max(1, int(round(seconds / hop)))) * hop
    return np.full(len(t), 2.0 * confidence - 1.0), t


def test_a_short_burst_of_near_certainty_commits(slow):
    """The meme case: a few seconds of the record is all the video contains."""
    trace = DopamineTrace(slow)
    trace.run(*_timeline(slow, seconds=4.0, confidence=0.97))
    assert trace.committed_by == "burst"
    assert trace.committed_at == pytest.approx(slow.da_burst_seconds, abs=0.2)


def test_the_burst_needs_the_whole_window(slow):
    """One very confident percept is not two seconds of them."""
    trace = DopamineTrace(slow)
    trace.run(*_timeline(slow, seconds=slow.da_burst_seconds * 0.5, confidence=1.0))
    assert trace.committed_at is None


def test_merely_suspicious_never_bursts(slow):
    """Sitting just under the cut must not accumulate into crossing it.

    Twenty seconds of 0.89 is a great deal of suspicion, and the whole point of
    a near-certainty rule is that it stays quiet for all of it. The length is
    kept inside the duration gate so this tests the cut rather than the gate.
    """
    assert 20.0 < slow.da_burst_max_seconds
    trace = DopamineTrace(slow)
    trace.run(*_timeline(slow, seconds=20.0, confidence=slow.da_burst_confidence - 0.04))
    assert trace.committed_at is None


def test_the_fast_path_is_only_for_short_recordings(slow):
    """The same evidence, once inside the gate and once outside it.

    A long video gives a sliding rule thousands of chances to fire, which is
    how an ungated fast path spends the specificity floor. Past the gate the
    slow pool is the only way in.
    """
    short = _timeline(slow, seconds=slow.da_burst_max_seconds - 2.0, confidence=0.99)
    long_ = _timeline(slow, seconds=slow.da_burst_max_seconds + 10.0, confidence=0.99)

    quick = DopamineTrace(slow)
    quick.run(*short)
    assert quick.committed_by == "burst"

    patient = DopamineTrace(slow)
    patient.run(*long_)
    assert patient.committed_by != "burst"


def test_a_long_track_still_commits_through_the_pool(config):
    """Sustained ordinary confidence is the slow path's job, and stays its job."""
    trace = DopamineTrace(config)
    trace.run(*_timeline(config, seconds=30.0, confidence=0.88))
    assert trace.committed_by == "pool"


def test_the_burst_can_be_switched_off(slow):
    from dataclasses import replace

    off = replace(slow, da_burst_seconds=0.0)
    trace = DopamineTrace(off)
    trace.run(*_timeline(off, seconds=4.0, confidence=1.0))
    assert trace.committed_at is None
