"""The circuit between the ear and the behaviour.

Three stages, each one a thing the fly actually has:

1. ``AntennalLobe``    gain control, so loud and quiet sound look alike.
2. ``KenyonCells``     a random sparse expansion, silenced down to a few
                       percent by one giant inhibitory neuron.
3. ``MBONCompartment`` a single output cell per compartment, reading the
                       Kenyon cells through synapses dopamine is allowed to
                       rewrite.

The first two never learn. In a fly they are fixed wiring, and the whole point
of the architecture is that only the last stage is plastic: a memory is a
pattern of weakened synapses, nothing else.
"""

from __future__ import annotations

import numpy as np

from brain.config import BrainConfig
from brain.memory import block_rows

_KC_GATHER_ROWS = 256
"""Percepts per claw-gather block.

The gather is the one expensive temporary in the model and this is the
measured sweet spot: at the default wiring a block costs 82 MB and the sweep
runs faster than at any larger size, because past a few tens of megabytes the
temporary stops fitting in cache and the loop turns into memory traffic. It is
a ceiling, not a promise -- brain.memory lowers it if the budget is tight.
"""

_KC_BLOCK = 2048
"""Percepts per winner-take-all block, to keep the drive matrix small.

Separate from the gather block because it bounds a different array: the drive
matrix and argpartition's index copy, which are (rows, n_kenyon) rather than
(rows, n_kenyon, n_claws), and so afford far more rows for the same bytes.
"""


def peak_working_bytes(
    config: BrainConfig, percepts: int, calibration_sample: int = 20_000
) -> dict[str, int]:
    """The transient arrays one pass through the calyx allocates.

    Reported rather than merely bounded, because a budget nobody checks is a
    comment. ``frrf-train`` prints these against the ceiling before it starts.
    """
    gather = block_rows(config.n_kenyon * config.n_claws * 4, _KC_GATHER_ROWS)
    winners = block_rows(config.n_kenyon * 12, _KC_BLOCK)
    return {
        "claw gather block": gather * config.n_kenyon * config.n_claws * 4,
        "threshold calibration": min(percepts, calibration_sample) * config.n_kenyon * 4,
        "winner-take-all block": winners * config.n_kenyon * 12,
    }


class AntennalLobe:
    """Divisive normalisation, after Olsen, Bhandawat & Wilson (2010).

    Each channel is divided by what the whole population is doing, so the
    output depends on the *shape* of the input rather than its level. A fly
    needs this because odour concentration varies over orders of magnitude.
    Here it is what makes the same song recognisable whether the upload is
    mastered hot or ripped at half volume.

    Channels normalise inside their own pool: mel bands against mel bands,
    pitch classes against pitch classes, one pool per sub-frame. Mixing them
    would divide amplitudes by a quantity in different units.
    """

    def __init__(self, config: BrainConfig, gains: np.ndarray | None = None) -> None:
        self.config = config
        self._blocks = config.blocks()
        self.gains = (
            np.ones(config.n_receptors, dtype=np.float32) if gains is None
            else np.asarray(gains, dtype=np.float32)
        )
        if self.gains.shape != (config.n_receptors,):
            raise ValueError(f"gains must have shape ({config.n_receptors},)")

    def calibrate(self, receptors: np.ndarray) -> None:
        """Homeostatic scaling: give every channel a comparable working point.

        Low mel bands carry far more energy than high ones in every recording
        ever made, so without this the top of the spectrum would never win a
        Kenyon cell. Real neurons do the same thing over days; this fly does
        it once, from the training corpus.
        """
        mean = np.asarray(receptors, dtype=np.float64).mean(axis=0)
        reference = np.median(mean[mean > 0]) if np.any(mean > 0) else 1.0
        self.gains = np.clip(reference / np.maximum(mean, 1e-8), 0.05, 20.0).astype(np.float32)

    def transform(self, receptors: np.ndarray) -> np.ndarray:
        """Receptor amplitudes in, projection-neuron activity in [0, r_max]."""
        config = self.config
        driven = np.asarray(receptors, dtype=np.float32) * self.gains
        powered = np.power(np.maximum(driven, 0.0), config.al_exponent)
        sigma = config.al_sigma ** config.al_exponent

        output = np.empty_like(powered)
        for lo, hi in self._blocks:
            pool = driven[:, lo:hi].sum(axis=1, keepdims=True)
            suppression = np.power(config.al_suppression * pool, config.al_exponent)
            output[:, lo:hi] = config.al_rmax * powered[:, lo:hi] / (
                powered[:, lo:hi] + sigma + suppression
            )
        return output


class KenyonCells:
    """A random sparse expansion, then near-total silence.

    Every Kenyon cell grows a handful of dendritic claws and each claw grabs
    one projection neuron more or less at random. Nobody chooses which. That
    random draw turns 180 correlated channels into 2,000 uncorrelated ones,
    and it is a locality-sensitive hash in the formal sense: similar input,
    similar set of winners (Dasgupta, Stevens & Navlakha, Science 2017).

    Then the APL neuron, a single cell innervating the entire lobe, feeds
    inhibition back and leaves only the strongest few percent firing. What
    comes out is a sparse binary tag; the fly's name for this particular
    sound.
    """

    def __init__(
        self,
        config: BrainConfig,
        claws: np.ndarray | None = None,
        thresholds: np.ndarray | None = None,
    ) -> None:
        self.config = config
        if claws is None:
            rng = np.random.default_rng(config.projection_seed)
            claws = np.stack(
                [rng.choice(config.n_receptors, size=config.n_claws, replace=False)
                 for _ in range(config.n_kenyon)]
            )
        self.claws = np.asarray(claws, dtype=np.int32)
        if self.claws.shape != (config.n_kenyon, config.n_claws):
            raise ValueError("claw table has the wrong shape for this configuration")
        self.thresholds = (
            np.zeros(config.n_kenyon, dtype=np.float32) if thresholds is None
            else np.asarray(thresholds, dtype=np.float32)
        )

    def calibrate(self, projection: np.ndarray, sample: int = 20_000) -> None:
        """Homeostatic intrinsic plasticity: even out who gets to fire.

        Claws are drawn at random, so some Kenyon cells end up sampling six
        loud low-frequency channels and win every competition while others
        never fire at all. A code where the same 1,150 cells carry every
        sound is a poor code. Giving each cell its own firing threshold, set
        so that it wins about ``kc_sparsity`` of the time on the training
        corpus, restores the population to full use.

        Excitability homeostasis of this kind is well established in neurons
        generally; for Kenyon cells specifically it is the least evidenced
        step in this model, and it is here because the code quality without
        it is measurably worse. See docs/BRAIN.md.
        """
        config = self.config
        rows = np.asarray(projection, dtype=np.float32)
        if rows.shape[0] > sample:
            rng = np.random.default_rng(config.projection_seed)
            rows = rows[rng.choice(rows.shape[0], size=sample, replace=False)]
        drive = self.drive(rows)
        # drive() just built this array for us and nobody else holds it, so
        # quantile may partition it in place instead of taking its own copy.
        self.thresholds = np.quantile(
            drive, 1.0 - config.kc_sparsity, axis=0, overwrite_input=True
        ).astype(np.float32)

    def drive(self, projection: np.ndarray) -> np.ndarray:
        """Summed claw input per Kenyon cell, before inhibition.

        Gathered in row blocks. ``projection[:, self.claws]`` builds the whole
        ``(percepts, n_kenyon, n_claws)`` array before the sum touches it, and
        at the default wiring that is 320 kB per percept; unblocked, the
        threshold calibration alone asked for 6.4 GB. The sum runs along the
        claw axis, so no output element is computed from a different set of
        numbers in a different order than before: the blocked result is
        bit-identical to the unblocked one.
        """
        projection = np.asarray(projection, dtype=np.float32)
        n_kenyon, n_claws = self.claws.shape
        n = projection.shape[0]
        out = np.empty((n, n_kenyon), dtype=np.float32)
        rows = block_rows(n_kenyon * n_claws * projection.itemsize, _KC_GATHER_ROWS)
        for start in range(0, n, rows):
            stop = min(start + rows, n)
            out[start:stop] = projection[start:stop][:, self.claws].sum(axis=2)
        return out

    def respond(self, projection: np.ndarray) -> np.ndarray:
        """Which cells fire, shape (n_percepts, n_active_kenyon).

        The APL winner-take-all is applied per percept, so exactly
        ``n_active_kenyon`` cells fire no matter how loud the input was. Since
        the count is fixed, the population is stored as the indices of the
        winners rather than as a mostly-zero vector: it is what the fly's
        downstream synapses address, it is what the interface draws, and it
        is twenty times smaller.
        """
        config = self.config
        k = config.n_active_kenyon
        n = projection.shape[0]
        out = np.empty((n, k), dtype=np.int32)
        # Four bytes of drive per cell, plus argpartition's eight bytes of
        # index for the copy it returns.
        rows = block_rows(config.n_kenyon * 12, _KC_BLOCK)
        for start in range(0, n, rows):
            stop = min(start + rows, n)
            drive = self.drive(projection[start:stop]) - self.thresholds
            out[start:stop] = np.argpartition(drive, -k, axis=1)[:, -k:]
        return out

    def densify(self, active: np.ndarray) -> np.ndarray:
        """Expand an index array back into a binary population vector.

        Only needed for inspection and for the tests that check the sparse
        and dense forms agree.
        """
        active = np.asarray(active)
        dense = np.zeros((active.shape[0], self.config.n_kenyon), dtype=np.float32)
        np.put_along_axis(dense, active, 1.0, axis=1)
        return dense


class MBONCompartment:
    """One mushroom body output neuron and the synapses that feed it.

    The mushroom body lobes are cut into compartments, each with its own MBON
    and its own dopaminergic neurons, and each MBON pushes behaviour one way:
    towards the thing or away from it. Learning is subtraction. Dopamine
    released in a compartment depresses exactly those Kenyon cell synapses
    that were active at the time, so an experienced smell stops driving the
    response it used to drive.
    """

    def __init__(self, name: str, config: BrainConfig, weights: np.ndarray | None = None) -> None:
        self.name = name
        self.config = config
        self.weights = (
            np.full(config.n_kenyon, config.w_baseline, dtype=np.float32) if weights is None
            else np.asarray(weights, dtype=np.float32)
        )

    def respond(self, active: np.ndarray) -> np.ndarray:
        """Mean weight over the Kenyon cells that are firing.

        ``active`` holds the indices of the winners, one row per percept.
        """
        return self.weights[np.asarray(active)].mean(axis=1)

    def depress(self, active: np.ndarray, dopamine: np.ndarray) -> None:
        """Dopamine-gated depression of the coincidentally active synapses.

        ``dopamine`` is one release level per percept. A synapse moves only
        where its Kenyon cell fired *and* dopamine was present, which is the
        coincidence detection the fly's plasticity rule is built on. A cell
        that fires for several percepts in the batch is depressed once per
        percept, which is why this accumulates rather than assigns.
        """
        config = self.config
        active = np.asarray(active)
        per_synapse = np.repeat(np.asarray(dopamine, dtype=np.float64), active.shape[1])
        delta = np.bincount(
            active.ravel(), weights=per_synapse, minlength=config.n_kenyon
        ).astype(np.float32)
        self.weights -= config.learning_rate * delta
        np.clip(self.weights, config.w_min, config.w_max, out=self.weights)

    def recover(self, steps: int = 1) -> None:
        """Drift back towards baseline; the reason fly memories fade.

        ``steps`` presentations of recovery are applied in one go, and the
        compounding is exact rather than linear. Linearly, a batch of a
        thousand presentations at a rate of 0.0015 would move a synapse 150
        percent of the way to baseline and overshoot it.
        """
        config = self.config
        fraction = 1.0 - (1.0 - config.recovery_rate) ** max(steps, 0)
        self.weights += fraction * (config.w_baseline - self.weights)
        np.clip(self.weights, config.w_min, config.w_max, out=self.weights)
