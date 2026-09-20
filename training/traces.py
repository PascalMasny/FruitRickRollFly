"""Out-of-fold confidence over time, kept so it can be re-read.

Cross-validation is the expensive part of this project and its real product is
not the fold table: it is one confidence timeline per track, produced by
weights that never saw that track. Everything downstream -- the ROC curves,
the commitment rule, the plots -- is a function of those timelines and nothing
else.

Training used to discard them, so asking "what would a threshold of 0.5 have
caught" meant thirteen folds of retraining to answer. Writing them next to the
model turns that into a file read, and it is a small file: one float32 pair per
percept, well under a megabyte for the whole corpus.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np


@dataclass
class Trace:
    """One track's out-of-fold confidence over time."""

    id: str
    title: str
    group: str
    kind: str
    positive: bool
    t: np.ndarray
    confidence: np.ndarray

    def __len__(self) -> int:
        return len(self.t)


def save(path: str | Path, families: dict[str, list[Trace]]) -> Path:
    """Write every family's traces to one compressed archive.

    Timelines differ in length from track to track, so they are stored
    concatenated with an offset table rather than as an object array: it keeps
    ``allow_pickle=False`` available on the way back in, which is worth more
    than the convenience.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    payload: dict[str, np.ndarray] = {}
    meta: dict[str, list[dict]] = {}
    for family, traces in families.items():
        payload[f"{family}.t"] = (
            np.concatenate([tr.t for tr in traces]).astype(np.float32)
            if traces else np.empty(0, dtype=np.float32)
        )
        payload[f"{family}.confidence"] = (
            np.concatenate([tr.confidence for tr in traces]).astype(np.float32)
            if traces else np.empty(0, dtype=np.float32)
        )
        payload[f"{family}.offsets"] = np.cumsum(
            [0, *(len(tr) for tr in traces)], dtype=np.int64
        )
        meta[family] = [
            {
                "id": tr.id, "title": tr.title, "group": tr.group,
                "kind": tr.kind, "positive": bool(tr.positive),
            }
            for tr in traces
        ]
    payload["meta"] = np.array(json.dumps(meta))
    np.savez_compressed(path, **payload)
    return path


def load(path: str | Path) -> dict[str, list[Trace]]:
    """Read back what :func:`save` wrote."""
    with np.load(path, allow_pickle=False) as data:
        meta = json.loads(str(data["meta"]))
        families: dict[str, list[Trace]] = {}
        for family, entries in meta.items():
            t = data[f"{family}.t"]
            confidence = data[f"{family}.confidence"]
            offsets = data[f"{family}.offsets"]
            families[family] = [
                Trace(
                    **entry,
                    t=t[offsets[i] : offsets[i + 1]],
                    confidence=confidence[offsets[i] : offsets[i + 1]],
                )
                for i, entry in enumerate(entries)
            ]
    return families
