"""Dopamine: the teaching signal, and the thing the app is really about.

Two jobs, and they are genuinely different.

During training, dopaminergic neurons carry a *prediction error*. A fly does
not release dopamine because something good happened; it releases dopamine
because something better than expected happened. Felsenberg and colleagues
showed this directly in Drosophila in 2018: the same DANs that write a memory
also revise it when the prediction turns out wrong. Two clusters split the
sign between them. PAM neurons signal better-than-expected and innervate the
compartments whose MBONs drive avoidance; PPL1 neurons signal
worse-than-expected and innervate the compartments whose MBONs drive
approach. Either way the synaptic effect is depression, and the behavioural
result is a shift in valence.

During listening, dopamine is an accumulator. One percept is 800 ms of sound
and the fly is not asked to bet its life on it; the pool integrates the
evidence and the animal commits when it crosses threshold. That crossing is
what this project reports as reaction time.

The accumulator subtracts a tonic baseline before it integrates, so evidence
weaker than the baseline drains it. This is both the textbook
evidence-accumulation-to-bound account of a perceptual decision and the way
dopaminergic neurons actually behave: they fire constantly, and only the
phasic excursion above that background carries a signal.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass

import numpy as np

from brain.config import BrainConfig


@dataclass(frozen=True)
class DopamineRelease:
    """One presentation's worth of dopamine, split by cluster.

    ``pam`` depresses the avoidance compartment, ``ppl1`` depresses the
    approach compartment. Both are non-negative; the sign of the error lives
    in which one is non-zero.
    """

    pam: np.ndarray
    ppl1: np.ndarray

    @property
    def magnitude(self) -> float:
        return float(np.abs(self.pam).mean() + np.abs(self.ppl1).mean())


def prediction_error(
    valence: np.ndarray, target: np.ndarray, weight: np.ndarray | None = None
) -> DopamineRelease:
    """Turn what the fly predicted, and what was true, into dopamine.

    ``target`` is +1 for a Rickroll and -1 for anything else. ``weight``
    rescales individual presentations, which is how the corpus is kept
    balanced without throwing training data away.
    """
    error = np.asarray(target, dtype=np.float32) - np.asarray(valence, dtype=np.float32)
    if weight is not None:
        error = error * np.asarray(weight, dtype=np.float32)
    return DopamineRelease(pam=np.maximum(error, 0.0), ppl1=np.maximum(-error, 0.0))


class DopamineTrace:
    """The pool that turns a stream of percepts into one decision.

    A leaky integrator, driven by positive valence and drained by its own time
    constant. ``aversion`` is the mirror image, driven by negative valence,
    and it is why the fly visibly recoils from a lecture recording instead of
    merely failing to get excited.
    """

    def __init__(self, config: BrainConfig | None = None) -> None:
        self.config = config or BrainConfig()
        self.reset()

    def reset(self) -> None:
        self.dopamine = 0.0
        self.aversion = 0.0
        self.committed_at: float | None = None
        self.committed_by: str | None = None
        self._last_t: float | None = None
        self._recent: deque[tuple[float, float]] = deque()
        self._streak = 0.0
        """Seconds of unbroken near-certainty. Accumulated as elapsed time
        rather than counted in percepts, because the hop differs between
        training and listening and a run counted in percepts would silently
        mean two different durations."""
        self._burst_allowed = True
        """Set by :meth:`run`, which is the only caller that knows how long the
        recording is. Stepping one percept at a time leaves it on."""

    def _burst(self, confidence: float, t: float) -> bool:
        """The fast path: a short stretch of near-certainty.

        Kept in seconds rather than in percepts because the hop differs between
        training and listening -- 255 ms against 128 ms -- and a rule counted in
        percepts would silently mean two different durations.
        """
        window = self.config.da_burst_seconds
        if window <= 0 or not self._burst_allowed:
            return False
        self._recent.append((t, confidence))
        # Keep the shortest run of percepts that still covers the window. The
        # test is against the *second* entry, not the first: dropping whenever
        # the first falls outside the window leaves the buffer permanently one
        # hop short of spanning it, and the rule below can then never be true.
        while len(self._recent) > 1 and t - self._recent[1][0] >= window:
            self._recent.popleft()
        # Until the buffer actually spans the window there is nothing to judge:
        # one very confident percept is not two seconds of them.
        if t - self._recent[0][0] < window:
            return False
        mean = sum(c for _, c in self._recent) / len(self._recent)
        return mean >= self.config.da_burst_confidence

    def _streak_holds(self, confidence: float, dt: float) -> bool:
        """The third path: near-certainty held without a break.

        Unlike the burst this is not gated on the length of the recording, and
        it is the only path that can fire on a sting buried in a long video --
        the shape of the most ordinary Rickroll there is. It can afford to be
        ungated because it asks a much harder question than a windowed mean: a
        mean can be carried by one spike, and a long video supplies thousands
        of windows to find a spike in, whereas a run has to survive every
        percept it covers.
        """
        need = self.config.da_streak_seconds
        if need <= 0:
            return False
        if confidence >= self.config.da_streak_confidence:
            self._streak += dt
        else:
            self._streak = 0.0
        return self._streak >= need

    def step(self, evidence: float, t: float) -> tuple[float, float]:
        """Advance the pool to time ``t`` under the current evidence.

        ``evidence`` runs from -1 to +1 and is how much more than a coin flip
        the fly currently believes. Both pools are floored at zero: a
        neurotransmitter pool cannot hold a negative amount of anything.
        """
        config = self.config
        dt = config.window_hop_seconds if self._last_t is None else max(t - self._last_t, 0.0)
        self._last_t = t

        decay = float(np.exp(-dt / config.da_tau)) if config.da_tau > 0 else 0.0
        charge = 1.0 - decay
        gain, baseline = config.da_gain, config.da_baseline
        slope = max(config.da_slope, 1e-6)

        # A saturating input curve, so a full pool is worth 1.0 whatever the
        # baseline is and the commit threshold reads as a fraction of total
        # charge. Past a few points of confidence either side of the baseline
        # the drive is all the way on or all the way off, which turns the pool
        # into a running measure of how often the fly is saying yes.
        excite = float(np.tanh((evidence - baseline) / slope))
        avoid = float(np.tanh((-evidence - baseline) / slope))

        self.dopamine = max(0.0, self.dopamine * decay + charge * gain * excite)
        self.aversion = max(0.0, self.aversion * decay + charge * gain * avoid)

        # Three ways to commit, and the pool is asked first so that a track
        # long enough to convince it reports the reaction time it always did.
        confidence = (evidence + 1.0) / 2.0
        # The streak is advanced whatever else happens, so that a commit which
        # arrives through another path does not leave it half counted.
        streak = self._streak_holds(confidence, dt)
        if self.committed_at is None:
            if self.dopamine >= config.da_commit:
                self.committed_at, self.committed_by = t, "pool"
            elif self._burst(confidence, t):
                self.committed_at, self.committed_by = t, "burst"
            elif streak:
                self.committed_at, self.committed_by = t, "streak"
        return self.dopamine, self.aversion

    def run(self, evidence: np.ndarray, times: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """Replay a whole timeline. Returns ``(dopamine, aversion)``."""
        self.reset()
        # The fast path is for recordings too short for the pool to charge. On
        # a long one it only adds chances to be wrong, so it is switched off.
        limit = self.config.da_burst_max_seconds
        self._burst_allowed = limit <= 0 or (len(times) > 0 and float(times[-1]) <= limit)
        dopamine = np.empty(len(evidence), dtype=np.float32)
        aversion = np.empty(len(evidence), dtype=np.float32)
        for i, (e, t) in enumerate(zip(evidence, times, strict=True)):
            dopamine[i], aversion[i] = self.step(float(e), float(t))
        return dopamine, aversion
