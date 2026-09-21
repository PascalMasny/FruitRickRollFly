"""Which fly the server is using, and what else is on the shelf.

Training writes a model to wherever it was told to, so `models/` accumulates
flies: one per sense, per experiment, per attempt. The server used to load
exactly one path and had no opinion about the rest. This finds all of them,
reads what each one claims about itself, and remembers which is in use.

The choice is stored on disk rather than in memory, because "which fly is
answering" should survive a restart and should be greppable afterwards.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODEL_DIR = ROOT / "models"
CHOICE_PATH = ROOT / "data" / "active-models.json"

SENSES = ("ear", "eye")
DEFAULTS = {"ear": "fly_brain.npz", "eye": "fly_eye.npz"}


@dataclass(frozen=True)
class ModelInfo:
    name: str
    sense: str
    path: Path
    trained: str | None
    target: str | None
    tracks: int | None
    percepts: int | None
    epochs: int | None
    kenyon: int | None
    bytes: int
    metrics: dict | None

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "sense": self.sense,
            "trained": self.trained,
            "target": self.target,
            "tracks": self.tracks,
            "percepts": self.percepts,
            "epochs": self.epochs,
            "kenyonCells": self.kenyon,
            "bytes": self.bytes,
            "scores": self.metrics,
        }


def _metrics_beside(path: Path) -> dict | None:
    """The metrics file a training run wrote next to this model, if it did.

    `fly_brain.npz` pairs with `metrics.json` and anything else pairs with
    `metrics-<stem>.json`, which is the convention the training commands
    already follow.
    """
    candidates = [MODEL_DIR / f"metrics-{path.stem}.json"]
    if path.stem == "fly_brain":
        candidates.append(MODEL_DIR / "metrics.json")
    for candidate in candidates:
        if candidate.exists():
            try:
                report = json.loads(candidate.read_text())
            except json.JSONDecodeError:
                continue
            return {
                family: {
                    "macroAuc": report.get(key, {}).get("macro_auc"),
                    "recall": report.get(key, {}).get("tracks", {}).get("recall"),
                    "specificity": report.get(key, {}).get("tracks", {}).get("specificity"),
                }
                for family, key in (
                    ("rendition", "unheard_rendition"),
                    ("upload", "unheard_upload"),
                )
                if report.get(key)
            } or None
    return None


def _describe(path: Path) -> ModelInfo | None:
    import numpy as np

    try:
        with np.load(path, allow_pickle=False) as data:
            if "metadata" not in data or "config" not in data:
                return None
            metadata = json.loads(str(data["metadata"]))
            config = json.loads(str(data["config"]))
    except Exception:
        return None

    return ModelInfo(
        name=path.name,
        # Models trained before the sense was recorded are ears: there has
        # never been a shipped eye.
        sense=metadata.get("sense", "ear"),
        path=path,
        trained=metadata.get("trained"),
        target=metadata.get("target"),
        tracks=metadata.get("tracks"),
        percepts=metadata.get("percepts"),
        epochs=metadata.get("epochs"),
        kenyon=config.get("n_kenyon"),
        bytes=path.stat().st_size,
        metrics=_metrics_beside(path),
    )


def available() -> list[ModelInfo]:
    """Every readable fly in models/, newest first."""
    found = [info for path in sorted(MODEL_DIR.glob("*.npz")) if (info := _describe(path))]
    return sorted(found, key=lambda m: (m.sense, m.trained or "", m.name), reverse=True)


def _choice() -> dict:
    if CHOICE_PATH.exists():
        try:
            return json.loads(CHOICE_PATH.read_text())
        except json.JSONDecodeError:
            return {}
    return {}


def active(sense: str = "ear") -> Path | None:
    """The chosen model for a sense, or the conventional default."""
    chosen = _choice().get(sense)
    if chosen:
        candidate = MODEL_DIR / Path(chosen).name
        if candidate.exists():
            return candidate
    fallback = MODEL_DIR / DEFAULTS[sense]
    return fallback if fallback.exists() else None


def choose(sense: str, name: str | None) -> Path | None:
    """Pick a model for a sense. `None` goes back to the default."""
    if sense not in SENSES:
        raise ValueError(f"sense must be one of {SENSES}")
    choice = _choice()
    if name is None:
        choice.pop(sense, None)
    else:
        candidate = MODEL_DIR / Path(name).name
        if not candidate.exists() or _describe(candidate) is None:
            raise FileNotFoundError(f"no readable model called {name}")
        choice[sense] = candidate.name
    CHOICE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CHOICE_PATH.write_text(json.dumps(choice, indent=2) + "\n")
    return active(sense)


def state() -> dict:
    return {
        "models": [m.to_dict() for m in available()],
        "active": {
            sense: (path.name if (path := active(sense)) else None) for sense in SENSES
        },
        "senses": list(SENSES),
    }
