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
    threshold put out of reach, and the streak switched off, so only the burst
    can fire.
    """
    from dataclasses import replace

    return replace(config, da_tau=2.0, da_baseline=0.72, da_commit=0.85,
                   da_streak_seconds=0.0)


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
    how an ungated windowed mean spends the specificity floor. Past the gate
    this path is shut; the streak, which asks a harder question, is the one
    that stays open (see below).
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


# ── the streak: near-certainty held without a break ─────────────────────────
# The only path that does not care how long the video is, and the only one that
# can catch four seconds of the record buried in eleven minutes of something
# else -- which is the most ordinary Rickroll there is.


@pytest.fixture
def patient(config):
    """A fly whose pool and burst are both out of reach, so only a streak fires."""
    from dataclasses import replace

    return replace(config, da_tau=2.0, da_baseline=0.72, da_commit=0.85,
                   da_burst_seconds=0.0)


def test_a_streak_of_near_certainty_commits(patient):
    trace = DopamineTrace(patient)
    trace.run(*_timeline(patient, seconds=2.0, confidence=0.99))
    assert trace.committed_by == "streak"
    assert trace.committed_at == pytest.approx(patient.da_streak_seconds, abs=0.2)


def test_the_streak_does_not_care_how_long_the_video_is(patient):
    """The whole point. A sting inside something long is still a sting.

    The burst is gated at twenty-five seconds, so before this path existed the
    same evidence was caught in a short video and missed in a long one.
    """
    hop = patient.window_hop_seconds
    quiet, loud = 0.30, 0.99
    for total in (10.0, 600.0):
        n = int(round(total / hop))
        confidence = np.full(n, quiet)
        # four seconds of the record, a long way in
        start = min(n - int(4.0 / hop) - 1, int(160.0 / hop))
        confidence[start : start + int(4.0 / hop)] = loud
        trace = DopamineTrace(patient)
        trace.run(2.0 * confidence - 1.0, np.arange(n) * hop)
        assert trace.committed_by == "streak", f"missed the sting in a {total:.0f}s video"


def test_a_broken_run_does_not_count(patient):
    """Sixty percepts of near-certainty, never two in a row, is not a streak.

    A windowed mean would be carried over the line by these; that is exactly
    the difference, and why this path can be ungated when the mean cannot.
    """
    hop = patient.window_hop_seconds
    confidence = np.full(400, 0.30)
    confidence[::4] = 1.0
    trace = DopamineTrace(patient)
    trace.run(2.0 * confidence - 1.0, np.arange(400) * hop)
    assert trace.committed_at is None


def test_just_under_the_bar_never_streaks(patient):
    trace = DopamineTrace(patient)
    trace.run(*_timeline(patient, seconds=60.0,
                         confidence=patient.da_streak_confidence - 0.02))
    assert trace.committed_at is None


def test_the_streak_can_be_switched_off(patient):
    from dataclasses import replace

    off = replace(patient, da_streak_seconds=0.0)
    trace = DopamineTrace(off)
    # Two seconds: long enough for the streak had it been on, short enough
    # that the pool cannot reach an out-of-reach threshold by itself.
    trace.run(*_timeline(off, seconds=2.0, confidence=1.0))
    assert trace.committed_at is None
