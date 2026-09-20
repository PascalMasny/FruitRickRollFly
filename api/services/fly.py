"""The one fly the server keeps.

Loading is lazy and cached: the model is 40 kB of NumPy, but the process
should still fail loudly at first use rather than silently serve a brain that
has never learned anything.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from brain.model import FlyBrain

ROOT = Path(__file__).resolve().parents[2]
MODEL_PATH = ROOT / "models" / "fly_brain.npz"
METRICS_PATH = ROOT / "models" / "metrics.json"
CACHE_DIR = ROOT / "data" / "cache"


class UntrainedFly(RuntimeError):
    """No trained model on disk."""


@lru_cache(maxsize=1)
def fly() -> FlyBrain:
    if not MODEL_PATH.exists():
        raise UntrainedFly(
            f"no fly at {MODEL_PATH}. Run 'frrf-fetch' then 'frrf-train' first."
        )
    return FlyBrain.load(MODEL_PATH)


@lru_cache(maxsize=1)
def metrics() -> dict:
    if not METRICS_PATH.exists():
        return {}
    return json.loads(METRICS_PATH.read_text())


def _evaluation(block: dict | None) -> dict | None:
    if not block:
        return None
    return {
        "macroAuc": block.get("macro_auc"),
        "tracks": block.get("tracks"),
        "percepts": block.get("percepts"),
        "medianFirstSuspicion": block.get("median_first_suspicion"),
    }


def card() -> dict:
    """What the interface needs to draw the brain and describe the model."""
    brain = fly()
    config = brain.config
    report = metrics()
    return {
        "target": brain.metadata.get("target", "unknown"),
        "trained": brain.metadata.get("trained"),
        "calibration": brain.metadata.get("calibration"),
        "corpus": {
            "tracks": brain.metadata.get("tracks"),
            "percepts": brain.metadata.get("percepts"),
        },
        "circuit": {
            "receptors": config.n_receptors,
            "melBands": config.n_mel,
            "chromaBands": config.n_chroma,
            "subframes": config.subframes,
            "kenyonCells": config.n_kenyon,
            "claws": config.n_claws,
            "activeKenyonCells": config.n_active_kenyon,
            "compartments": list(config.compartments),
            "windowSeconds": round(config.window_seconds, 3),
            "hopSeconds": round(config.window_hop_seconds, 3),
            "commitThreshold": config.da_commit,
            "dopamineTau": config.da_tau,
        },
        "performance": {
            # Two evaluations, deliberately both shown. "unheard upload" is
            # what the box in front of the user is doing; "unheard rendition"
            # is the harder question of whether the fly knows the song rather
            # than the recording. See docs/TRAINING.md.
            "unheardUpload": _evaluation(report.get("unheard_upload")),
            "unheardRendition": _evaluation(report.get("unheard_rendition")),
            "commitment": report.get("commitment", {}).get("tuned_on"),
        },
    }
