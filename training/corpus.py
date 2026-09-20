"""The corpus: what is in it, where it lives, and how it is split.

Two rules govern everything here, and both exist because getting them wrong
produces a number that looks wonderful and means nothing.

**Split by group, never by video.** Twelve of the positives are the same 1987
master recording uploaded twelve times. Split those at random and the test set
is the training set with a different thumbnail.

**No compilation may be a negative.** A greatest-hits upload labelled *other*
would teach the fly that the song it is looking for is not the song it is
looking for.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "training" / "manifest.json"
AUDIO_DIR = ROOT / "data" / "audio"
FEATURE_DIR = ROOT / "data" / "features"

MAX_TRACK_SECONDS = 480.0
"""Long uploads are truncated. A two-thousand-second lecture would otherwise
supply a fifth of the negative class on its own, and the fly would learn a
great deal about that one speaker's room."""

POSITIVE = "rickroll"


@dataclass(frozen=True)
class Track:
    id: str
    label: str
    group: str
    kind: str
    use: str
    title: str

    @property
    def is_positive(self) -> bool:
        return self.label == POSITIVE

    @property
    def target(self) -> float:
        return 1.0 if self.is_positive else -1.0

    @property
    def watch_url(self) -> str:
        return f"https://www.youtube.com/watch?v={self.id}"

    def feature_path(self, directory: Path = FEATURE_DIR) -> Path:
        return directory / f"{self.id}.npz"

    def audio_path(self, directory: Path = AUDIO_DIR) -> Path:
        hits = sorted(directory.glob(f"{self.id}.*"))
        return hits[0] if hits else directory / f"{self.id}.audio"


@dataclass(frozen=True)
class Manifest:
    target: str
    curated: str
    curation_rules: list[str]
    tracks: list[Track]
    include_holdout: bool = False
    """Whether ``use: holdout`` tracks count as trainable.

    Held at load time rather than passed around, because everything that
    builds a fold -- :meth:`trainable`, :meth:`groups`, and the fold functions
    that call them -- has to agree about it. A corpus that disagrees with its
    own splits is the one bug in this file worth designing against."""

    @classmethod
    def load(cls, path: Path = MANIFEST, include_holdout: bool = False) -> Manifest:
        raw = json.loads(Path(path).read_text())
        return cls(
            target=raw["target"],
            curated=raw["curated"],
            curation_rules=raw["curation_rules"],
            tracks=[Track(**entry) for entry in raw["tracks"]],
            include_holdout=include_holdout,
        )

    def trainable(self) -> list[Track]:
        """Tracks fit to learn from; the demo-only ones are held back.

        ``holdout`` tracks are curated and fetched but excluded by default:
        they are hard negatives the circuit has been measured failing to
        separate, and letting them in is a deliberate experiment rather than
        the normal run. See docs/FINDINGS.md.
        """
        allowed = {"train", "holdout"} if self.include_holdout else {"train"}
        return [t for t in self.tracks if t.use in allowed]

    def groups(self, label: str | None = None) -> list[str]:
        seen: list[str] = []
        for track in self.trainable():
            if label and track.label != label:
                continue
            if track.group not in seen:
                seen.append(track.group)
        return seen


@dataclass
class Corpus:
    """Percepts, labels, and the bookkeeping needed to split them honestly."""

    receptors: np.ndarray
    target: np.ndarray
    track_index: np.ndarray
    tracks: list[Track]

    @property
    def groups(self) -> np.ndarray:
        lookup = [t.group for t in self.tracks]
        return np.array([lookup[i] for i in self.track_index])

    def mask_for_groups(self, groups: set[str]) -> np.ndarray:
        return np.isin(self.groups, list(groups))

    def balance_weights(self) -> np.ndarray:
        """One weight per percept, so both classes pull equally hard.

        There are four times as many negative percepts as positive ones, and
        an unweighted corpus would teach the fly that the safest answer is
        always no.
        """
        weights = np.ones(len(self.target), dtype=np.float32)
        for sign in (1.0, -1.0):
            mask = self.target == sign
            count = int(mask.sum())
            if count:
                weights[mask] = len(self.target) / (2.0 * count)
        return weights


def load_corpus(
    tracks: list[Track], directory: Path = FEATURE_DIR
) -> Corpus:
    """Read cached percepts for the given tracks into one corpus."""
    receptors: list[np.ndarray] = []
    target: list[np.ndarray] = []
    index: list[np.ndarray] = []
    present: list[Track] = []

    for track in tracks:
        path = track.feature_path(directory)
        if not path.exists():
            continue
        with np.load(path) as data:
            block = data["receptors"]
        if block.shape[0] == 0:
            continue
        position = len(present)
        present.append(track)
        receptors.append(block)
        target.append(np.full(block.shape[0], track.target, dtype=np.float32))
        index.append(np.full(block.shape[0], position, dtype=np.int32))

    if not present:
        raise FileNotFoundError(
            f"no cached percepts in {directory}; run 'frrf-fetch' first"
        )
    return Corpus(
        receptors=np.concatenate(receptors),
        target=np.concatenate(target),
        track_index=np.concatenate(index),
        tracks=present,
    )
