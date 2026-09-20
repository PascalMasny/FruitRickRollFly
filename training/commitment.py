"""Tune the two commit rules against short clips, and show what they cost.

Finding 6 added a second way to commit, for the shape most Rickrolls in the
wild actually have: a few seconds of the record stapled to the end of something
else, far too short for a leaky pool with a two second time constant to charge.
The sweep behind that rule was never committed, which left its one published
number -- two seconds averaging 0.93 -- unreproducible and, as its own caveat
admitted, fitted to a single video that scored 0.934.

This rebuilds the experiment so the number can be argued with.

Every clip is cut from the out-of-fold timelines in ``models/traces.npz``, so
no confidence here was ever produced by weights that had seen the track. Memes
are simulated the way memes are made: filler, then a sting of the record. Short
negatives are windows of the same lengths cut from ordinary tracks, because a
rule aimed at fifteen second memes has to be judged against fifteen second
non-memes and the manifest contains none.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, replace
from pathlib import Path

import numpy as np

from brain.config import BrainConfig
from brain.dopamine import DopamineTrace
from training import traces as traces_io


@dataclass(frozen=True)
class Clip:
    """One short video, as the confidence timeline the fly would have seen."""

    t: np.ndarray
    confidence: np.ndarray
    meme: bool
    seconds: float


def _hop(trace: traces_io.Trace) -> float:
    return float(np.median(np.diff(trace.t))) if len(trace) > 1 else 0.255


def build_clips(
    families: dict[str, list[traces_io.Trace]],
    *,
    memes: int,
    negatives: int,
    sting: tuple[float, float],
    filler: tuple[float, float],
    negative_span: tuple[float, float],
    seed: int,
    from_opening: bool = True,
    opening_seconds: float = 20.0,
    positives_from: str = "upload",
) -> list[Clip]:
    """Cut a short-clip population out of the out-of-fold timelines."""
    """Which family the sting comes from is the whole argument, not a detail.

    A track appears in both families with two different out-of-fold
    confidences, because the folds are built differently, and quietly keeping
    whichever came first mixes two populations that mean opposite things.
    Memes are cut from ``upload``: somebody pasting a Rickroll link is pasting
    an upload of the 1987 master, which is what that family is. Cutting them
    from ``rendition`` would be asking how often the fly spots a piano cover
    spliced into a meme, which is not a thing that happens.
    """
    if positives_from not in families:
        raise SystemExit(f"no {positives_from!r} family in the traces")
    positives = [tr for tr in families[positives_from] if tr.positive and len(tr) > 8]
    others = [
        tr for family in families.values() for tr in family if not tr.positive and len(tr) > 8
    ]
    if not positives or not others:
        raise SystemExit("need both positive and negative traces to build clips")

    rng = np.random.default_rng(seed)
    clips: list[Clip] = []

    def window(trace: traces_io.Trace, seconds: float, *, opening: bool = False) -> np.ndarray:
        hop = _hop(trace)
        n = max(1, int(round(seconds / hop)))
        if n >= len(trace):
            return trace.confidence
        # A real Rickroll splices in the front of the record -- the line
        # everyone knows -- so the sting carries the intro's ramp rather than
        # starting mid-chorus at full confidence. Sampling anywhere in the
        # track makes the population far easier than the thing it stands for.
        limit = min(len(trace) - n, max(1, int(round(opening_seconds / hop)))) if opening \
            else len(trace) - n
        start = int(rng.integers(0, max(1, limit)))
        return trace.confidence[start : start + n]

    for _ in range(memes):
        record = positives[int(rng.integers(0, len(positives)))]
        cover = others[int(rng.integers(0, len(others)))]
        hop = _hop(record)
        lead = window(cover, float(rng.uniform(*filler)))
        tail = window(record, float(rng.uniform(*sting)), opening=from_opening)
        confidence = np.concatenate([lead, tail])
        t = np.arange(len(confidence), dtype=np.float32) * hop
        clips.append(Clip(t, confidence.astype(np.float32), True, float(t[-1])))

    for _ in range(negatives):
        track = others[int(rng.integers(0, len(others)))]
        hop = _hop(track)
        confidence = window(track, float(rng.uniform(*negative_span)))
        t = np.arange(len(confidence), dtype=np.float32) * hop
        clips.append(Clip(t, confidence.astype(np.float32), False, float(t[-1])))

    return clips


def judge(clips: list[Clip], config: BrainConfig) -> dict:
    """Run every clip through the real commit logic, both paths live."""
    hits = misses = false_alarms = quiet = 0
    by_path = {"pool": 0, "burst": 0}
    fp_path = {"pool": 0, "burst": 0}
    latencies: list[float] = []
    for clip in clips:
        trace = DopamineTrace(config)
        trace.run(2.0 * clip.confidence - 1.0, clip.t)
        committed = trace.committed_at is not None
        if clip.meme and committed:
            hits += 1
            by_path[trace.committed_by] = by_path.get(trace.committed_by, 0) + 1
            latencies.append(float(trace.committed_at))
        elif clip.meme:
            misses += 1
        elif committed:
            false_alarms += 1
            fp_path[trace.committed_by] = fp_path.get(trace.committed_by, 0) + 1
        else:
            quiet += 1
    memes = hits + misses
    negatives = false_alarms + quiet
    return {
        "recall": hits / memes if memes else 0.0,
        "specificity": quiet / negatives if negatives else 0.0,
        "median_latency": float(np.median(latencies)) if latencies else None,
        "p90_latency": float(np.percentile(latencies, 90)) if latencies else None,
        "memes": memes,
        "negatives": negatives,
        "hits_by_path": by_path,
        "false_alarms_by_path": fp_path,
    }


def sweep(clips: list[Clip], base: BrainConfig, windows, thresholds, floor: float) -> list[dict]:
    rows = []
    for window in windows:
        for threshold in thresholds:
            config = replace(base, da_burst_seconds=window, da_burst_confidence=threshold)
            row = judge(clips, config) | {"window": window, "threshold": threshold}
            row["passes"] = row["specificity"] >= floor
            rows.append(row)
    return rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--traces", type=Path, default=Path("models/traces.npz"))
    parser.add_argument("--memes", type=int, default=4000)
    parser.add_argument("--negatives", type=int, default=9000)
    parser.add_argument("--seed", type=int, default=1987)
    parser.add_argument("--floor", type=float, default=0.95,
                        help="specificity the short-clip population must keep")
    parser.add_argument("--sting", type=float, nargs=2, default=(3.0, 9.0),
                        help="seconds of the record spliced in")
    parser.add_argument("--filler", type=float, nargs=2, default=(0.0, 12.0))
    parser.add_argument("--negative-span", type=float, nargs=2, default=(5.0, 25.0))
    parser.add_argument("--sting-anywhere", action="store_true",
                        help="cut the sting from anywhere in the record rather than its opening")
    parser.add_argument("--opening-seconds", type=float, default=20.0)
    parser.add_argument("--positives-from", default="upload", choices=("upload", "rendition"),
                        help="which out-of-fold family the sting is cut from")
    parser.add_argument("--json", type=Path, default=None)
    args = parser.parse_args(argv)

    families = traces_io.load(args.traces)
    clips = build_clips(
        families,
        memes=args.memes,
        negatives=args.negatives,
        sting=tuple(args.sting),
        filler=tuple(args.filler),
        negative_span=tuple(args.negative_span),
        seed=args.seed,
        from_opening=not args.sting_anywhere,
        opening_seconds=args.opening_seconds,
        positives_from=args.positives_from,
    )
    base = BrainConfig()
    print(f"{len(clips)} clips: {args.memes} simulated memes, {args.negatives} short negatives")
    print(f"sting {args.sting[0]:.0f}-{args.sting[1]:.0f}s, filler {args.filler[0]:.0f}-"
          f"{args.filler[1]:.0f}s, negatives {args.negative_span[0]:.0f}-"
          f"{args.negative_span[1]:.0f}s\n")

    shipped = judge(clips, base)
    print(f"shipped rule ({base.da_burst_seconds}s @ {base.da_burst_confidence}): "
          f"recall {shipped['recall']:.3f}  specificity {shipped['specificity']:.3f}  "
          f"median {shipped['median_latency']:.1f}s\n")

    windows = [1.5, 2.0, 2.5, 3.0]
    thresholds = [round(x, 3) for x in np.arange(0.84, 0.961, 0.01)]
    rows = sweep(clips, base, windows, thresholds, args.floor)

    print(f"{'window':>7} {'thresh':>7} {'recall':>8} {'specif':>8} {'median':>8} {'p90':>7}  ok")
    for row in rows:
        median = f"{row['median_latency']:.1f}s" if row["median_latency"] else "   -"
        p90 = f"{row['p90_latency']:.1f}s" if row["p90_latency"] else "   -"
        print(f"{row['window']:7.1f} {row['threshold']:7.2f} {row['recall']:8.3f} "
              f"{row['specificity']:8.3f} {median:>8} {p90:>7}  {'yes' if row['passes'] else ''}")

    ok = [r for r in rows if r["passes"]]
    best = max(ok, key=lambda r: r["recall"]) if ok else None
    if best:
        print(f"\nbest rule holding specificity >= {args.floor}: "
              f"{best['window']}s @ {best['threshold']} -> recall {best['recall']:.3f}, "
              f"specificity {best['specificity']:.3f}, median {best['median_latency']:.1f}s")
    else:
        print(f"\nno rule holds specificity >= {args.floor}")

    if args.json:
        args.json.write_text(json.dumps({"shipped": shipped, "sweep": rows, "best": best},
                                        indent=2, default=float) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
