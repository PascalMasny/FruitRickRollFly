"""Scoring, kept separate so the numbers in the README are one function call."""

from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np


def auc(score: np.ndarray, positive: np.ndarray) -> float:
    """Rank-based ROC AUC; ties handled by averaging ranks."""
    score = np.asarray(score, dtype=np.float64)
    positive = np.asarray(positive, dtype=bool)
    n_pos, n_neg = int(positive.sum()), int((~positive).sum())
    if n_pos == 0 or n_neg == 0:
        return float("nan")
    order = np.argsort(score, kind="mergesort")
    ranks = np.empty(len(score), dtype=np.float64)
    ranks[order] = np.arange(1, len(score) + 1)
    # Average the ranks inside each tied block, or a flat scorer looks good.
    sorted_scores = score[order]
    start = 0
    for stop in range(1, len(score) + 1):
        if stop == len(score) or sorted_scores[stop] != sorted_scores[start]:
            if stop - start > 1:
                ranks[order[start:stop]] = ranks[order[start:stop]].mean()
            start = stop
    return float((ranks[positive].sum() - n_pos * (n_pos + 1) / 2) / (n_pos * n_neg))


@dataclass
class PerceptScore:
    """How the fly did on individual 800 ms percepts."""

    count: int
    accuracy: float
    recall: float
    specificity: float
    auc: float

    def to_dict(self) -> dict:
        return asdict(self)


def score_percepts(confidence: np.ndarray, target: np.ndarray, cut: float = 0.5) -> PerceptScore:
    positive = np.asarray(target) > 0
    called = np.asarray(confidence) >= cut
    recall = float(called[positive].mean()) if positive.any() else float("nan")
    specificity = float((~called[~positive]).mean()) if (~positive).any() else float("nan")
    return PerceptScore(
        count=int(len(confidence)),
        accuracy=float((called == positive).mean()),
        recall=recall,
        specificity=specificity,
        auc=auc(confidence, positive),
    )


@dataclass
class TrackScore:
    """How the fly did on whole videos, which is what the app reports."""

    count: int
    accuracy: float
    recall: float
    specificity: float
    median_latency: float | None
    p90_latency: float | None

    def to_dict(self) -> dict:
        return asdict(self)


def score_tracks(verdicts: list[dict]) -> TrackScore:
    """``verdicts`` come from :func:`training.train.track_verdicts`."""
    if not verdicts:
        return TrackScore(0, float("nan"), float("nan"), float("nan"), None, None)
    positive = np.array([v["positive"] for v in verdicts], dtype=bool)
    called = np.array([v["committed"] for v in verdicts], dtype=bool)
    hits = [v["latency"] for v in verdicts if v["positive"] and v["latency"] is not None]
    return TrackScore(
        count=len(verdicts),
        accuracy=float((called == positive).mean()),
        recall=float(called[positive].mean()) if positive.any() else float("nan"),
        specificity=float((~called[~positive]).mean()) if (~positive).any() else float("nan"),
        median_latency=float(np.median(hits)) if hits else None,
        p90_latency=float(np.percentile(hits, 90)) if hits else None,
    )
