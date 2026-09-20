"""The fly.

``FlyBrain`` wires the ear, the gain control, the calyx and the output
compartments into one object, and gives it the three verbs the rest of the
project needs: ``encode`` a sound, ``learn`` from it, ``listen`` to a file and
report what happened.

The saved form is a single ``.npz``: the claw table, the Kenyon thresholds,
the receptor gains, one weight vector per compartment, and the configuration
that produced them. A fly is about 100 kB.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from brain.audio import JohnstonsOrgan
from brain.config import BrainConfig
from brain.dopamine import DopamineTrace, prediction_error
from brain.layers import AntennalLobe, KenyonCells, MBONCompartment

MODEL_FORMAT = 2
"""Bumped whenever the saved layout changes in a way old files cannot satisfy."""


@dataclass
class Response:
    """What the fly did while a track played.

    One entry per percept. ``t`` is the moment the percept ended, which is the
    earliest the fly could have known anything about it.
    """

    t: np.ndarray
    valence: np.ndarray
    confidence: np.ndarray
    dopamine: np.ndarray
    aversion: np.ndarray
    approach: np.ndarray
    avoidance: np.ndarray
    kenyon: np.ndarray
    ear: np.ndarray
    committed_at: float | None

    def __len__(self) -> int:
        return len(self.t)

    @property
    def peak_confidence(self) -> float:
        return float(self.confidence.max()) if len(self) else 0.0

    @property
    def verdict(self) -> bool:
        return self.committed_at is not None


class FlyBrain:
    """A Drosophila mushroom body that has an opinion about one song."""

    def __init__(self, config: BrainConfig | None = None) -> None:
        self.config = config or BrainConfig()
        self.ear = JohnstonsOrgan(self.config)
        self.antennal_lobe = AntennalLobe(self.config)
        self.kenyon = KenyonCells(self.config)
        self.compartments = {
            name: MBONCompartment(name, self.config) for name in self.config.compartments
        }
        # Valence is bounded by construction; the readout only has to map it
        # onto a probability. Two scalars, fitted after training.
        self.readout_gain = 4.0
        self.readout_bias = 0.0
        self.metadata: dict = {}

    # ── perception ───────────────────────────────────────────────────────────

    def calibrate(self, receptors: np.ndarray) -> None:
        """Set the two fixed-wiring calibrations from a corpus of percepts."""
        self.antennal_lobe.calibrate(receptors)
        self.kenyon.calibrate(self.antennal_lobe.transform(receptors))

    def encode(self, receptors: np.ndarray, block: int = 8192) -> np.ndarray:
        """Receptor percepts in, Kenyon cell tags out, as active indices."""
        receptors = np.asarray(receptors, dtype=np.float32)
        chunks = [
            self.kenyon.respond(self.antennal_lobe.transform(receptors[i : i + block]))
            for i in range(0, len(receptors), block)
        ]
        if not chunks:
            return np.empty((0, self.config.n_active_kenyon), dtype=np.int32)
        return np.concatenate(chunks)

    def valence(self, kenyon: np.ndarray) -> np.ndarray:
        """Approach drive minus avoidance drive, one value per percept."""
        return (
            self.compartments["approach"].respond(kenyon)
            - self.compartments["avoidance"].respond(kenyon)
        )

    def confidence(self, valence: np.ndarray) -> np.ndarray:
        """Valence squashed into the probability the app shows as a percentage.

        The readout gain runs into the dozens, because valence lives in a
        narrow band, so the argument is clipped before it reaches ``exp``.
        Beyond that range the answer is zero or one to far more digits than a
        float32 keeps.
        """
        z = self.readout_gain * np.asarray(valence, dtype=np.float64) + self.readout_bias
        return (1.0 / (1.0 + np.exp(-np.clip(z, -60.0, 60.0)))).astype(np.float32)

    # ── learning ─────────────────────────────────────────────────────────────

    def learn(
        self,
        kenyon: np.ndarray,
        target: np.ndarray,
        weight: np.ndarray | None = None,
        batch: int = 64,
        rng: np.random.Generator | None = None,
    ) -> float:
        """One pass over a set of percepts. Returns the mean absolute error.

        Presentations are shuffled and fed in small batches, because a fly
        meets one smell at a time and the depression rule is local: the order
        matters, and a whole-corpus update would not be the same algorithm.
        """
        rng = rng or np.random.default_rng()
        order = rng.permutation(len(kenyon))
        approach = self.compartments["approach"]
        avoidance = self.compartments["avoidance"]
        total = 0.0

        for start in range(0, len(order), batch):
            index = order[start : start + batch]
            kc = kenyon[index]
            release = prediction_error(
                self.valence(kc),
                np.asarray(target)[index],
                None if weight is None else np.asarray(weight)[index],
            )
            # PAM depresses avoidance, PPL1 depresses approach. The
            # asymmetry is the whole of the fly's valence system.
            avoidance.depress(kc, release.pam)
            approach.depress(kc, release.ppl1)
            # Recovery is per presentation, not per epoch. Depression alone
            # would floor every synapse at zero within one pass over the
            # corpus; it is the balance between the two that stores anything.
            for compartment in self.compartments.values():
                compartment.recover(steps=len(index))
            total += release.magnitude * len(index)

        return total / max(len(order), 1)

    def fit_readout(
        self,
        valence: np.ndarray,
        target: np.ndarray,
        weight: np.ndarray | None = None,
        steps: int = 25,
    ) -> None:
        """Fit the two readout scalars so that confidence means something.

        Weighted logistic regression on one feature, solved by Newton steps.
        It calibrates the number the interface prints; it adds no capacity,
        because there is one feature and the fly already produced it.

        The weights default to class-balanced, and that detail is the whole
        point. Only 29 percent of the corpus is the song, so an unweighted fit
        learns a prior of 0.29 and parks the intercept low enough that
        confidence never reaches one half. The circuit underneath was
        separating the classes at 0.95 AUC while the interface reported
        no every single time.
        """
        v = np.asarray(valence, dtype=np.float64)
        y = (np.asarray(target, dtype=np.float64) > 0).astype(np.float64)
        if weight is None:
            weight = np.ones_like(y)
            for value in (0.0, 1.0):
                mask = y == value
                if mask.any():
                    weight[mask] = len(y) / (2.0 * mask.sum())
        w = np.asarray(weight, dtype=np.float64)

        design = np.stack([v, np.ones_like(v)], axis=1)
        beta = np.array([float(self.readout_gain), float(self.readout_bias)])
        for _ in range(steps):
            p = 1.0 / (1.0 + np.exp(-np.clip(design @ beta, -30.0, 30.0)))
            gradient = design.T @ (w * (p - y))
            hessian = design.T @ (design * (w * p * (1.0 - p))[:, None])
            hessian += np.eye(2) * 1e-6
            step = np.linalg.solve(hessian, gradient)
            beta -= step
            if np.abs(step).max() < 1e-9:
                break
        self.readout_gain, self.readout_bias = float(beta[0]), float(beta[1])

    # ── listening ────────────────────────────────────────────────────────────

    def respond(self, receptors: np.ndarray, t: np.ndarray) -> Response:
        """Run a percept stream through the circuit and the dopamine pool."""
        projection = self.antennal_lobe.transform(np.asarray(receptors, dtype=np.float32))
        kenyon = self.kenyon.respond(projection)
        approach = self.compartments["approach"].respond(kenyon)
        avoidance = self.compartments["avoidance"].respond(kenyon)
        valence = approach - avoidance

        confidence = self.confidence(valence)
        # The pool integrates calibrated evidence, not raw valence. Valence is
        # in whatever units the weights happen to have settled into; evidence
        # is "how much more than a coin flip", which is what a reaction time
        # should be measured against.
        trace = DopamineTrace(self.config)
        dopamine, aversion = trace.run(2.0 * confidence - 1.0, t)

        # One channel bank for the interface to draw, averaged over the
        # sub-frames of each percept: 48 tonotopic channels and 12 pitch
        # classes, already bounded by the gain control.
        config = self.config
        width = config.channels_per_subframe
        ear = projection.reshape(len(projection), config.subframes, width).mean(axis=1)

        return Response(
            t=np.asarray(t, dtype=np.float32),
            valence=valence.astype(np.float32),
            confidence=confidence,
            dopamine=dopamine,
            aversion=aversion,
            approach=approach.astype(np.float32),
            avoidance=avoidance.astype(np.float32),
            kenyon=kenyon,
            ear=ear.astype(np.float32),
            committed_at=trace.committed_at,
        )

    def listen(self, path: str | Path) -> Response:
        """Decode an audio file and respond to all of it."""
        receptors, t = self.ear.percepts_from_file(path)
        return self.respond(receptors, t)

    # ── persistence ──────────────────────────────────────────────────────────

    def save(self, path: str | Path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "format": np.int32(MODEL_FORMAT),
            "config": np.array(json.dumps(self.config.to_dict())),
            "metadata": np.array(json.dumps(self.metadata)),
            "receptor_gains": self.antennal_lobe.gains,
            "claws": self.kenyon.claws,
            "kenyon_thresholds": self.kenyon.thresholds,
            "readout": np.array([self.readout_gain, self.readout_bias], dtype=np.float32),
        }
        for name, compartment in self.compartments.items():
            payload[f"weights_{name}"] = compartment.weights
        np.savez_compressed(path, **payload)
        return path

    @classmethod
    def load(cls, path: str | Path) -> FlyBrain:
        with np.load(path, allow_pickle=False) as data:
            stored = int(data["format"])
            if stored != MODEL_FORMAT:
                raise ValueError(
                    f"{path} is a format {stored} fly, this code reads format {MODEL_FORMAT}"
                )
            config = BrainConfig.from_dict(json.loads(str(data["config"])))
            brain = cls(config)
            brain.metadata = json.loads(str(data["metadata"]))
            brain.antennal_lobe.gains = data["receptor_gains"]
            brain.kenyon.claws = data["claws"]
            brain.kenyon.thresholds = data["kenyon_thresholds"]
            brain.readout_gain, brain.readout_bias = (float(x) for x in data["readout"])
            for name in config.compartments:
                brain.compartments[name].weights = data[f"weights_{name}"]
        return brain
