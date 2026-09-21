"""Teach the fly, then find out what it is actually worth.

The honest numbers and the shipped model come out of the same script, in that
order, because the temptation to quote a number the shipped model never earned
is otherwise irresistible.

Two questions get asked, and they are not the same question.

**Unheard rendition.** Leave-one-group-out over the positives: hide every
recording of one performance, train on the rest, ask about what was hidden.
The fold that hides the twelve uploads of the 1987 master hides 57 percent of
the positive class, and is the hardest fold that can be built out of this
corpus. This is the question "would it know the song if it had only ever
heard other people play it".

**Unheard upload.** Hold out whole uploads of the master recording that other
uploads of the same master stay in training for. This is leakage in the strict
sense and it is stated as such; it is also exactly what happens in the
application, where the link someone pastes is nearly always that record
arriving as a re-encode, a remaster, or a lyric video. It answers "would it
know the record through a different upload's compression".

Confidences are pooled across folds, never valences. Each fold trains its own
MBON weights, so a valence of 0.1 in one fold has no relation to a valence of
0.1 in another; only after each fold's own readout has mapped valence to a
probability are the numbers on one scale.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass, replace
from pathlib import Path

import numpy as np

from brain.config import BrainConfig
from brain.dopamine import DopamineTrace
from brain.layers import peak_working_bytes
from brain.memory import (
    ALLOCATOR_HEADROOM,
    budget_bytes,
    budget_gb,
    human,
    peak_rss_bytes,
    set_budget,
)
from brain.model import FlyBrain
from training.corpus import ROOT, Corpus, Manifest, Track, load_corpus
from training.metrics import score_percepts, score_tracks
from training.traces import Trace
from training.traces import save as save_traces

MODEL_PATH = ROOT / "models" / "fly_brain.npz"
METRICS_PATH = ROOT / "models" / "metrics.json"
TRACES_PATH = ROOT / "models" / "traces.npz"
STUDIO_GROUP = "studio-1987"

MIN_SPECIFICITY = 0.95
"""Track-level specificity the commit rule must reach on held-out negatives
before recall is even looked at. A false positive is the failure that matters
here: the entire point of the interface is that the fly stays bored.

It is measured on the **upload** folds, not the rendition folds, and the
reason is worth stating. Every upload fold trains on nine other uploads of the
master, which is the condition the deployed fly is in. One rendition fold hides
the master entirely, and the negatives that happen to be held out alongside it
are then judged by a fly that has never heard the song at all. Those
false positives are real, but they are not the deployed model's, and letting
them set the threshold made the fly four times slower for nothing. The upload
folds cover all 41 negative groups exactly once between them, so nothing is
lost by measuring there."""

MIN_UPLOAD_RECALL = 1.0
"""And it must still catch every held-out upload of the record. A rule that
buys specificity by missing the actual Rickroll has missed the point."""

LATENCY_SLACK = 1.0
"""Seconds of reaction time worth trading for better rendition recall."""


@dataclass
class Fold:
    name: str
    held_out_groups: set[str]
    held_out_ids: set[str]

    def mask(self, corpus: Corpus) -> np.ndarray:
        ids = np.array([corpus.tracks[i].id for i in corpus.track_index])
        return np.isin(corpus.groups, list(self.held_out_groups)) | np.isin(
            ids, list(self.held_out_ids)
        )


def rendition_folds(manifest: Manifest) -> list[Fold]:
    """One fold per positive group, each taking a slice of the negatives along."""
    positives = manifest.groups(label="rickroll")
    negatives = manifest.groups(label="other")
    return [
        Fold(
            name=group,
            held_out_groups={group} | set(negatives[i :: len(positives)]),
            held_out_ids=set(),
        )
        for i, group in enumerate(positives)
    ]


def upload_folds(manifest: Manifest, per_fold: int = 3) -> list[Fold]:
    """Folds over individual uploads of the master recording."""
    uploads = [t.id for t in manifest.trainable() if t.group == STUDIO_GROUP]
    negatives = manifest.groups(label="other")
    folds = []
    for i in range(0, len(uploads), per_fold):
        chunk = uploads[i : i + per_fold]
        share = set(negatives[i // per_fold :: max(1, len(uploads) // per_fold)])
        folds.append(
            Fold(
                name=f"uploads {i + 1}-{i + len(chunk)}",
                held_out_groups=share,
                held_out_ids=set(chunk),
            )
        )
    return folds


def train_brain(
    config: BrainConfig, corpus: Corpus, train_mask: np.ndarray, epochs: int, seed: int
) -> FlyBrain:
    """Calibrate the fixed wiring, then run dopamine over the training percepts.

    Calibration uses only the training split. Receptor gains and Kenyon
    thresholds are fitted quantities like any other, and fitting them on the
    test set would leak the test set.
    """
    brain = FlyBrain(config)
    brain.calibrate(corpus.receptors[train_mask])

    kenyon = brain.encode(corpus.receptors)
    weights = corpus.balance_weights()
    rng = np.random.default_rng(seed)
    for _ in range(epochs):
        brain.learn(kenyon[train_mask], corpus.target[train_mask], weights[train_mask], rng=rng)

    brain.fit_readout(brain.valence(kenyon[train_mask]), corpus.target[train_mask])
    return brain


def macro_auc(reports: list[dict]) -> float:
    """Average of the per-fold AUCs.

    The headline number, because it never compares a confidence produced by
    one fold's weights against one produced by another's. Pooling is reported
    too, and where the two disagree the pooled figure is the one carrying a
    calibration artefact.
    """
    values = [r["percepts"]["auc"] for r in reports if not np.isnan(r["percepts"]["auc"])]
    return float(np.mean(values)) if values else float("nan")


def cross_validate(
    config: BrainConfig,
    folds: list[Fold],
    corpus: Corpus,
    times: dict[str, np.ndarray],
    epochs: int,
    seed: int,
    label: str,
) -> tuple[list[dict], list[Trace]]:
    """Run every fold. Returns per-fold percept scores and the held-out traces."""
    reports: list[dict] = []
    traces: list[Trace] = []
    ids = np.array([corpus.tracks[i].id for i in corpus.track_index])

    for fold in folds:
        test_mask = fold.mask(corpus)
        train_mask = ~test_mask
        if not test_mask.any() or not train_mask.any():
            continue

        started = time.perf_counter()
        brain = train_brain(config, corpus, train_mask, epochs, seed)
        confidence = brain.confidence(brain.valence(brain.encode(corpus.receptors[test_mask])))

        held = np.flatnonzero(test_mask)
        for position, track in enumerate(corpus.tracks):
            rows = np.flatnonzero(test_mask & (corpus.track_index == position))
            if rows.size == 0:
                continue
            take = np.searchsorted(held, rows)
            traces.append(
                Trace(
                    id=track.id, title=track.title, group=track.group, kind=track.kind,
                    positive=track.is_positive, t=times[track.id], confidence=confidence[take],
                )
            )

        percept = score_percepts(confidence, corpus.target[test_mask])
        reports.append(
            {
                "fold": fold.name,
                "held_out_groups": sorted(fold.held_out_groups),
                "held_out_ids": sorted(fold.held_out_ids),
                "held_out_tracks": int(len(set(ids[test_mask]))),
                "seconds": round(time.perf_counter() - started, 1),
                "percepts": percept.to_dict(),
            }
        )
        print(
            f"  [{label}] {fold.name:24s} auc {percept.auc:.4f} acc {percept.accuracy:.3f} "
            f"recall {percept.recall:.3f} spec {percept.specificity:.3f} "
            f"({time.perf_counter() - started:.0f}s)"
        )
    return reports, traces


# ── turning confidence over time into one verdict ────────────────────────────


def verdicts_at(traces: list[Trace], config: BrainConfig) -> list[dict]:
    out = []
    for trace in traces:
        pool = DopamineTrace(config)
        pool.run(2.0 * trace.confidence - 1.0, trace.t)
        out.append(
            {
                "id": trace.id, "title": trace.title, "group": trace.group, "kind": trace.kind,
                "positive": trace.positive,
                "committed": pool.committed_at is not None,
                "latency": pool.committed_at,
                "peak_confidence": float(trace.confidence.max()),
                "mean_confidence": float(trace.confidence.mean()),
            }
        )
    return out


def tune_commitment(
    rendition_traces: list[Trace],
    upload_traces: list[Trace],
    config: BrainConfig,
    min_specificity: float = MIN_SPECIFICITY,
) -> tuple[BrainConfig, list[dict]]:
    """Choose the dopamine time constant, the tonic baseline and the threshold.

    These three numbers are a decision rule, not something the fly learns, and
    they are picked on out-of-fold traces: no fold ever saw its own track
    while its weights were being trained.

    The rule is picked in this order, and the order is the product decision
    written down.

    1. **Specificity at least** ``MIN_SPECIFICITY`` on the held-out negatives
       of the upload folds. A fly that shouts Rickroll at a Chopin nocturne is
       a worse product than one that misses a piano cover, so this is a
       constraint and not a term.
    2. **Every held-out upload of the record caught.** A rule that buys
       specificity by missing the actual Rickroll has missed the point.
    3. **Median latency on the held-out uploads**, minimised.
    4. **Recall on held-out renditions**, maximised among rules within
       ``LATENCY_SLACK`` of the quickest. Generalising to a piano cover is a
       bonus, and it is ranked like one.

    Three numbers chosen against 65 out-of-fold tracks is a mild optimism in
    the track-level figures. It is stated here rather than hidden; the percept
    AUCs are untouched by it.
    """
    curve = []
    candidates: list[tuple[float, float, BrainConfig]] = []

    for tau in (0.6, 0.9, 1.4, 2.0, 3.0, 4.5):
        for baseline in (0.5, 0.6, 0.66, 0.72, 0.78, 0.84, 0.9):
            for commit in (0.2, 0.3, 0.4, 0.5, 0.6, 0.75):
                candidate = replace(
                    config, da_tau=float(tau), da_baseline=float(baseline),
                    da_commit=float(commit),
                )
                rendition = score_tracks(verdicts_at(rendition_traces, candidate))
                upload = score_tracks(verdicts_at(upload_traces, candidate))
                latency = upload.median_latency if upload.median_latency is not None else 1e9
                curve.append(
                    {
                        "tau": tau, "baseline": baseline, "commit": commit,
                        "rendition_recall": rendition.recall,
                        "rendition_specificity": rendition.specificity,
                        "upload_recall": upload.recall,
                        "upload_specificity": upload.specificity,
                        "upload_latency": upload.median_latency,
                    }
                )
                if upload.specificity >= min_specificity and upload.recall >= MIN_UPLOAD_RECALL:
                    candidates.append((rendition.recall, latency, candidate))

    if not candidates:
        # A bare exception here throws away the one thing worth knowing: how
        # close anything got, and therefore whether this is a corpus problem or
        # a floor that needs moving. The traces are already on disk, so the
        # sweep can be re-run without retraining.
        viable = [c for c in curve if c["upload_recall"] >= MIN_UPLOAD_RECALL]
        best = max(viable, key=lambda c: c["upload_specificity"], default=None)
        reached = (
            f"the best any of the {len(curve)} rules manages is "
            f"{best['upload_specificity']:.3f} (tau {best['tau']}s, baseline "
            f"{best['baseline']}, threshold {best['commit']})"
            if best
            else "no rule catches every held-out upload at all"
        )
        raise SystemExit(
            f"No commit rule reaches the {min_specificity:.2f} specificity floor at "
            f"full upload recall: {reached}.\n"
            "The circuit is not separating the negatives it has been given. Either the "
            "corpus has gained hard negatives this representation cannot tell from the "
            "target, or the floor has to move -- see --min-specificity."
        )
    quickest = min(latency for _, latency, _ in candidates)
    shortlist = [c for c in candidates if c[1] <= quickest + LATENCY_SLACK]
    return max(shortlist, key=lambda item: (item[0], -item[1]))[2], curve


def check_budget(config: BrainConfig, percepts: int) -> None:
    """Project what training will hold at once, and refuse to start if it will
    not fit the ceiling.

    A memory limit nobody checks is a comment, and this one was earned. Moving
    the calyx to a whole animal's 4,000 Kenyon cells doubled a temporary that
    was already being gathered in one unblocked expression, the threshold
    calibration asked for 6.4 GB of it per fold, and a 16 GB machine went into
    swap.

    What is already resident here -- the interpreter, NumPy, the corpus, the
    percept times -- is measured rather than guessed. What is still to come is
    counted below, and the total carries ``ALLOCATOR_HEADROOM`` on top, because
    the arrays this function can name are not all the memory a run occupies.
    """
    k = config.n_active_kenyon
    resident = peak_rss_bytes()
    to_come = {
        # The training split, the float64 copy the gain control takes of it,
        # and the fold's slice of the tags. Charged at the size of the whole
        # corpus, which no single fold reaches.
        "fold copies": percepts * (config.n_receptors * 12 + k * 4),
        "kenyon tags": percepts * k * 4,
    }
    transient = peak_working_bytes(config, percepts)
    # The gather block lives inside both of the others, never beside them.
    concurrent = transient["claw gather block"] + max(
        transient["threshold calibration"], transient["winner-take-all block"]
    )
    projected = int((resident + sum(to_come.values()) + concurrent) * ALLOCATOR_HEADROOM)

    print(f"memory budget {budget_gb():.1f} GB, projected peak {human(projected)}")
    for name, size in (("resident now", resident), *to_come.items(), *transient.items()):
        print(f"    {name:24s} {human(size)}")

    if projected > budget_bytes():
        # stdout is block-buffered when redirected; without this the refusal
        # lands on stderr before the breakdown that justifies it.
        sys.stdout.flush()
        raise SystemExit(
            f"projected peak {human(projected)} exceeds the {budget_gb():.1f} GB budget. "
            f"Raise it with --memory-budget, or shrink the run with --kenyon."
        )


def _seconds(value: float | None) -> str:
    return "never" if value is None else f"{value:.1f}s"


def load_times(tracks: list[Track], directory: Path | None = None) -> dict[str, np.ndarray]:
    """Percept times, from the same directory the percepts themselves came from.

    The directory argument is not decoration. This used to read the default
    feature directory whatever `load_corpus` had been given, so training a
    second sense paired one sense's confidences with the other's clock -- which
    is a silent corruption everywhere the two happen to have the same number of
    percepts, and a crash only where they do not.
    """
    times = {}
    for track in tracks:
        path = track.feature_path() if directory is None else track.feature_path(directory)
        with np.load(path) as data:
            times[track.id] = data["t"]
    return times


def pooled(traces: list[Trace], config: BrainConfig) -> dict:
    confidence = np.concatenate([t.confidence for t in traces])
    target = np.concatenate(
        [np.full(len(t.confidence), 1.0 if t.positive else -1.0) for t in traces]
    )
    verdicts = verdicts_at(traces, config)
    suspicion = [
        float(t.t[np.flatnonzero(t.confidence >= 0.5)[0]])
        for t in traces
        if t.positive and np.any(t.confidence >= 0.5)
    ]
    return {
        "percepts": score_percepts(confidence, target).to_dict(),
        "tracks": score_tracks(verdicts).to_dict(),
        "median_first_suspicion": float(np.median(suspicion)) if suspicion else None,
        "verdicts": sorted(verdicts, key=lambda v: (not v["positive"], v["group"])),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Train the fly and score it honestly.")
    parser.add_argument("--epochs", type=int, default=60)
    parser.add_argument("--learning-rate", type=float, default=None)
    parser.add_argument("--recovery-rate", type=float, default=None)
    parser.add_argument("--claws", type=int, default=None)
    parser.add_argument("--sparsity", type=float, default=None)
    parser.add_argument("--kenyon", type=int, default=None)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument(
        "--min-specificity",
        type=float,
        default=MIN_SPECIFICITY,
        metavar="P",
        help=(
            f"track-level specificity the commit rule must reach on held-out uploads "
            f"before recall is looked at (default {MIN_SPECIFICITY}). Lowering it is a "
            "product decision, not a tuning knob: it is the promise that the fly stays "
            "bored."
        ),
    )
    parser.add_argument(
        "--memory-budget",
        type=float,
        default=None,
        metavar="GB",
        help=(
            f"ceiling on the training working set, in gigabytes "
            f"(default {budget_gb():.0f}; also settable as FRRF_MEMORY_BUDGET_GB). "
            "Block sizes are derived from it and the projected peak is checked "
            "against it before training starts."
        ),
    )
    parser.add_argument("--skip-cv", action="store_true", help="train only, do not score")
    parser.add_argument(
        "--with-holdout",
        action="store_true",
        help=(
            "train on the use=holdout hard negatives as well. They are the tracks "
            "this representation was measured unable to separate from the target, so "
            "expect the specificity floor to be unreachable; see docs/FINDINGS.md."
        ),
    )
    parser.add_argument(
        "--sense", choices=("ear", "eye"), default="ear",
        help="which sense the percepts came from; recorded in the model",
    )
    parser.add_argument(
        "--manifest", type=Path, default=None,
        help="corpus to train on; frrf-corrections writes one with the fixes folded in",
    )
    parser.add_argument(
        "--min-activity", type=float, default=0.0,
        help=(
            "drop tracks whose mean receptor activity is below this. For the eye, "
            "a still-image upload is not a hard example, it is an absent one"
        ),
    )
    parser.add_argument(
        "--features", type=Path, default=None,
        help="percept directory; data/features-eye trains the same circuit on sight",
    )
    parser.add_argument("--out", type=Path, default=MODEL_PATH)
    parser.add_argument("--metrics", type=Path, default=METRICS_PATH)
    parser.add_argument(
        "--traces",
        type=Path,
        default=TRACES_PATH,
        help=(
            "where to write the out-of-fold confidence timelines. They are the "
            "expensive product of cross-validation and everything downstream is "
            "a function of them, so they are kept rather than recomputed."
        ),
    )
    args = parser.parse_args(argv)
    if args.memory_budget is not None:
        set_budget(args.memory_budget)

    overrides = {
        "learning_rate": args.learning_rate, "recovery_rate": args.recovery_rate,
        "n_claws": args.claws, "kc_sparsity": args.sparsity, "n_kenyon": args.kenyon,
    }
    config = BrainConfig(**{k: v for k, v in overrides.items() if v is not None})

    manifest = (
        Manifest.load(args.manifest, include_holdout=args.with_holdout)
        if args.manifest is not None
        else Manifest.load(include_holdout=args.with_holdout)
    )
    trainable = manifest.trainable()
    if args.min_activity > 0:
        # A track with no motion carries no visual evidence either way, and in
        # this corpus being a still image is *correlated with being the target*
        # -- many Rickroll uploads are audio re-ups over a cover. Left in, the
        # circuit can learn that correlation, which is a fact about how the
        # corpus was collected and not about the song.
        kept = []
        for track in trainable:
            path = (
                track.feature_path() if args.features is None
                else track.feature_path(args.features)
            )
            if not path.exists():
                continue
            with np.load(path) as data:
                if float(data["receptors"].mean()) >= args.min_activity:
                    kept.append(track)
        print(f"{len(kept)}/{len(trainable)} tracks above activity {args.min_activity}")
        trainable = kept
    corpus = (
        load_corpus(trainable, args.features)
        if args.features is not None
        else load_corpus(trainable)
    )
    times = load_times(corpus.tracks, args.features)
    print(
        f"corpus: {len(corpus.target)} percepts from {len(corpus.tracks)} tracks, "
        f"{int((corpus.target > 0).sum())} rickroll / {int((corpus.target < 0).sum())} other"
    )
    check_budget(config, len(corpus.target))

    report: dict = {}
    if not args.skip_cv:
        rendition_reports, rendition_traces = cross_validate(
            config, rendition_folds(manifest), corpus, times, args.epochs, args.seed, "rendition"
        )
        upload_reports, upload_traces = cross_validate(
            config, upload_folds(manifest), corpus, times, args.epochs, args.seed, "upload"
        )

        save_traces(
            args.traces,
            {"rendition": rendition_traces, "upload": upload_traces},
        )
        print(f"saved {args.traces} ({args.traces.stat().st_size / 1024:.0f} kB)")

        config, curve = tune_commitment(
            rendition_traces, upload_traces, config, args.min_specificity
        )
        print(
            f"\ncommitment tuned on out-of-fold traces: tau {config.da_tau}s, "
            f"tonic baseline {config.da_baseline}, threshold {config.da_commit:.2f}"
        )

        rendition = pooled(rendition_traces, config)
        upload = pooled(upload_traces, config)
        for name, block, folds in (
            ("unheard rendition", rendition, rendition_reports),
            ("unheard upload", upload, upload_reports),
        ):
            p, tr = block["percepts"], block["tracks"]
            print(
                f"  {name:18s} macro auc {macro_auc(folds):.4f} (pooled {p['auc']:.4f}) | "
                f"track acc {tr['accuracy']:.3f} recall {tr['recall']:.3f} "
                f"spec {tr['specificity']:.3f} | first suspicion "
                f"{_seconds(block['median_first_suspicion'])} commit "
                f"{_seconds(tr['median_latency'])}"
            )
        report = {
            "unheard_rendition": {
                "folds": rendition_reports, "macro_auc": macro_auc(rendition_reports), **rendition
            },
            "unheard_upload": {
                "folds": upload_reports, "macro_auc": macro_auc(upload_reports), **upload
            },
            "commitment": {
                "tau": config.da_tau,
                "baseline": config.da_baseline,
                "threshold": config.da_commit,
                "tuned_on": (
                    "out-of-fold traces: specificity and recall on the rendition folds, "
                    "latency on the upload folds"
                ),
                "curve": curve,
            },
        }

    print("\ntraining the shipped fly on the whole corpus")
    everything = np.ones(len(corpus.target), dtype=bool)
    brain = train_brain(config, corpus, everything, args.epochs, args.seed)
    brain.metadata = {
        "target": manifest.target,
        "trained": time.strftime("%Y-%m-%d"),
        "epochs": args.epochs,
        "seed": args.seed,
        "tracks": len(corpus.tracks),
        "percepts": int(len(corpus.target)),
        "calibration": (
            "confidence is calibrated on the training corpus; the accuracy figures "
            "in metrics.json are out of fold"
        ),
    }
    brain.save(args.out)
    print(f"saved {args.out} ({args.out.stat().st_size / 1024:.0f} kB)")

    if report:
        payload = {"metadata": brain.metadata, "config": config.to_dict(), **report}
        args.metrics.parent.mkdir(parents=True, exist_ok=True)
        args.metrics.write_text(json.dumps(payload, indent=2))
        print(f"saved {args.metrics}")

    peak = peak_rss_bytes()
    verdict = "within" if peak <= budget_bytes() else "OVER"
    print(f"peak memory {human(peak)}, {verdict} the {budget_gb():.1f} GB budget")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
