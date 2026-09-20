"""Draw what cross-validation found, so the numbers can be argued with.

``pyproject.toml`` has promised a ``frrf-evaluate`` since the beginning and
this is it. It renders nothing it has not been given: every figure here is a
function of ``models/metrics.json`` and ``models/traces.npz``, both written by
``frrf-train``, and no figure retrains anything or touches the audio.

Four questions, four figures.

``roc``          Can the circuit separate the classes at all, per percept?
``folds``        And does that hold up fold by fold, or is one fold carrying it?
``commitment``   What did the decision rule cost, and what else was on offer?
``misses``       When the fly misses the song, where exactly does it go wrong?

The last one is the point of the whole exercise. Percept-level AUC is a
property of the circuit; whether the fly *says* Rickroll is a property of the
dopamine pool on top of it, and the two fail in different ways for different
reasons. A figure that shows only the first cannot tell you which one to fix.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from brain.config import BrainConfig
from brain.dopamine import DopamineTrace
from training.corpus import ROOT
from training.traces import Trace
from training.traces import load as load_traces

METRICS_PATH = ROOT / "models" / "metrics.json"
TRACES_PATH = ROOT / "models" / "traces.npz"
IMG_DIR = ROOT / "docs" / "img"

MIN_SPECIFICITY = 0.95
"""Mirrors the floor in training.train, so the figure draws the same line the
tuner was actually held to."""

# ── palette ──────────────────────────────────────────────────────────────────
# Slots 1 and 2 of the reference categorical palette, validated as a pair:
# worst CVD delta-E 24.7, worst normal-vision 33.6, both clear of the floors,
# and both over 3:1 on this surface. Colour follows the entity throughout --
# rendition is always blue and upload is always orange, in every figure, so a
# reader who learns the pairing once never has to relearn it.

SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_SOFT = "#52514e"
INK_FAINT = "#8a8880"
GRID = "#e6e5e1"
RENDITION = "#2a78d6"
UPLOAD = "#eb6834"
MUTED = "#c3c2bb"

STYLE = {
    "figure.facecolor": SURFACE,
    "axes.facecolor": SURFACE,
    "savefig.facecolor": SURFACE,
    "axes.edgecolor": GRID,
    "axes.labelcolor": INK_SOFT,
    "axes.titlecolor": INK,
    "axes.linewidth": 1.0,
    "axes.grid": True,
    "axes.axisbelow": True,
    "grid.color": GRID,
    "grid.linewidth": 1.0,
    "xtick.color": INK_SOFT,
    "ytick.color": INK_SOFT,
    "xtick.labelsize": 9,
    "ytick.labelsize": 9,
    "text.color": INK,
    "font.size": 10,
    "font.family": "sans-serif",
    "legend.frameon": False,
    "figure.dpi": 140,
}


def _style():
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update(STYLE)
    return plt


def _frame(ax, title: str, subtitle: str = "") -> None:
    """Recessive axes: two spines, a soft grid, the title carrying the point.

    The subtitle is offset in points rather than in axes fractions, because a
    fraction of a short axes is a different number of pixels than a fraction
    of a tall one and the title lands on top of it in exactly one of the two.
    """
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(GRID)
    rows = subtitle.count("\n") + 1 if subtitle else 0
    ax.set_title(title, fontsize=12, fontweight="bold", loc="left", pad=8 + 13 * rows)
    if subtitle:
        ax.annotate(
            subtitle, xy=(0, 1), xycoords="axes fraction",
            xytext=(0, 6), textcoords="offset points",
            fontsize=9.5, color=INK_SOFT, va="bottom", ha="left",
        )


# ── the curves ───────────────────────────────────────────────────────────────


def roc_curve(score: np.ndarray, positive: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """False positive rate against true positive rate, ties collapsed.

    Ties matter here rather than being a technicality: a saturating readout
    parks thousands of percepts at exactly 1.0, and a curve that stepped
    through them one at a time would draw a staircase the model has not
    earned.
    """
    score = np.asarray(score, dtype=np.float64)
    positive = np.asarray(positive, dtype=bool)
    order = np.argsort(-score, kind="mergesort")
    ranked, hit = score[order], positive[order]
    tp, fp = np.cumsum(hit), np.cumsum(~hit)
    edge = np.r_[np.diff(ranked) != 0, True]
    n_pos, n_neg = max(int(hit.sum()), 1), max(int((~hit).sum()), 1)
    return np.r_[0.0, fp[edge] / n_neg], np.r_[0.0, tp[edge] / n_pos]


def pooled(traces: list[Trace]) -> tuple[np.ndarray, np.ndarray]:
    confidence = np.concatenate([t.confidence for t in traces])
    positive = np.concatenate([np.full(len(t), t.positive, dtype=bool) for t in traces])
    return confidence, positive


def pool_of(trace: Trace, config: BrainConfig) -> tuple[np.ndarray, float | None]:
    """Replay the dopamine accumulator over one out-of-fold timeline."""
    pool = DopamineTrace(config)
    dopamine, _ = pool.run(2.0 * trace.confidence - 1.0, trace.t)
    return dopamine, pool.committed_at


# ── figures ──────────────────────────────────────────────────────────────────


def figure_roc(families: dict[str, list[Trace]], report: dict, path: Path) -> Path:
    plt = _style()
    fig, ax = plt.subplots(figsize=(6.4, 5.4))

    ax.plot([0, 1], [0, 1], color=INK_FAINT, linewidth=1.2, linestyle=(0, (4, 4)), zorder=1)
    ax.text(0.52, 0.47, "chance", color=INK_FAINT, fontsize=9, rotation=39,
            ha="center", va="top", rotation_mode="anchor")

    for family, colour, key in (
        ("rendition", RENDITION, "unheard_rendition"),
        ("upload", UPLOAD, "unheard_upload"),
    ):
        confidence, positive = pooled(families[family])
        fpr, tpr = roc_curve(confidence, positive)
        auc = report[key]["percepts"]["auc"]
        ax.plot(fpr, tpr, color=colour, linewidth=2, zorder=3,
                label=f"unheard {family}  (AUC {auc:.3f})")

    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1.005)
    ax.set_xlabel("false positive rate")
    ax.set_ylabel("true positive rate")
    ax.set_aspect("equal")
    ax.legend(loc="lower right", fontsize=9.5, labelcolor=INK)
    _frame(
        ax, "The circuit separates percepts it has never heard",
        "Pooled over every out-of-fold 800 ms percept. One curve per question.",
    )
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    return path


def figure_folds(report: dict, path: Path) -> Path:
    plt = _style()
    rows = [
        (f["fold"], f["percepts"]["auc"], colour)
        for key, colour in (("unheard_rendition", RENDITION), ("unheard_upload", UPLOAD))
        for f in report[key]["folds"]
    ]
    rows.sort(key=lambda r: r[1])
    labels = [r[0] for r in rows]
    values = [r[1] for r in rows]
    colours = [r[2] for r in rows]
    y = np.arange(len(rows))

    fig, ax = plt.subplots(figsize=(7.4, 0.42 * len(rows) + 2.0))
    ax.axvline(0.5, color=INK_FAINT, linewidth=1.2, linestyle=(0, (4, 4)), zorder=1)
    for yi, value, colour in zip(y, values, colours, strict=True):
        ax.plot([0.5, value], [yi, yi], color=colour, linewidth=2, alpha=0.35, zorder=2,
                solid_capstyle="round")
    ax.scatter(values, y, s=90, color=colours, zorder=3, edgecolor=SURFACE, linewidth=1.5)
    for yi, value in zip(y, values, strict=True):
        side, align = (0.012, "left") if value >= 0.5 else (-0.012, "right")
        ax.text(value + side, yi, f"{value:.3f}", va="center", ha=align,
                fontsize=9, color=INK)

    ax.set_yticks(y, labels, fontsize=9.5)
    ax.set_xlim(0.22, 1.03)
    ax.set_xlabel("held-out percept AUC")
    ax.set_ylim(-0.8, len(rows) - 0.2)
    ax.grid(axis="y", visible=False)
    ax.text(0.5, len(rows) - 0.38, "chance", color=INK_FAINT, fontsize=9,
            ha="center", va="top")

    handles = [
        plt.Line2D([], [], marker="o", linestyle="", markersize=9, color=RENDITION,
                   label="unheard rendition"),
        plt.Line2D([], [], marker="o", linestyle="", markersize=9, color=UPLOAD,
                   label="unheard upload"),
    ]
    ax.legend(handles=handles, loc="lower right", fontsize=9.5, labelcolor=INK)
    _frame(
        ax, "The average hides the spread",
        "Every upload fold is excellent. Two rendition folds are at or below chance.",
    )
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    return path


def figure_commitment(report: dict, path: Path) -> Path:
    """Every commit rule the tuner considered, and the one it kept.

    The constraint is drawn rather than described. What the eye should catch is
    how much rendition recall sits just left of the specificity floor, which is
    the trade the product rule makes on purpose.
    """
    plt = _style()
    curve = report["commitment"]["curve"]
    chosen = report["commitment"]

    feasible = [c for c in curve if c["upload_specificity"] >= MIN_SPECIFICITY
                and c["upload_recall"] >= 1.0]
    rejected = [c for c in curve if c not in feasible]

    fig, ax = plt.subplots(figsize=(7.0, 5.2))
    ax.axvspan(MIN_SPECIFICITY, 1.02, color=RENDITION, alpha=0.05, zorder=0)
    ax.axvline(MIN_SPECIFICITY, color=INK_FAINT, linewidth=1.2, linestyle=(0, (4, 4)), zorder=1)

    ax.scatter([c["upload_specificity"] for c in rejected],
               [c["rendition_recall"] for c in rejected],
               s=34, color=MUTED, zorder=2, label="rule rejected by the floor")
    ax.scatter([c["upload_specificity"] for c in feasible],
               [c["rendition_recall"] for c in feasible],
               s=44, color=RENDITION, alpha=0.85, zorder=3,
               edgecolor=SURFACE, linewidth=0.8, label="rule allowed by the floor")

    here = [c for c in curve
            if c["tau"] == chosen["tau"] and c["baseline"] == chosen["baseline"]
            and c["commit"] == chosen["threshold"]]
    if here:
        pick = here[0]
        ax.scatter([pick["upload_specificity"]], [pick["rendition_recall"]],
                   s=190, facecolor="none", edgecolor=UPLOAD, linewidth=2.4, zorder=4)
        ax.annotate(
            f"chosen: tau {chosen['tau']}s, baseline {chosen['baseline']}, "
            f"threshold {chosen['threshold']:.2f}",
            xy=(pick["upload_specificity"], pick["rendition_recall"]),
            xytext=(-14, 30), textcoords="offset points",
            fontsize=9.5, color=INK, ha="right",
            arrowprops={"arrowstyle": "-", "color": UPLOAD, "linewidth": 1.4},
        )

    ax.text(MIN_SPECIFICITY + 0.005, 1.015, f"specificity floor {MIN_SPECIFICITY:.2f}",
            fontsize=9, color=INK_FAINT, ha="left", va="top")
    ax.set_xlabel("specificity on held-out uploads")
    ax.set_ylabel("recall on held-out renditions")
    ax.set_xlim(min(c["upload_specificity"] for c in curve) - 0.02, 1.02)
    ax.set_ylim(-0.03, 1.03)
    ax.legend(loc="lower left", fontsize=9.5, labelcolor=INK)
    _frame(
        ax, "What the commit rule cost",
        f"All {len(curve)} candidate rules. Recall on unheard renditions is ranked last, "
        "behind\nspecificity and latency, and this is what that ordering bought.",
    )
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    return path


def figure_misses(families: dict[str, list[Trace]], report: dict, path: Path) -> Path:
    """Why the misses are not a perception failure.

    Each panel is one held-out positive the fly never committed to. The pale
    line is what the circuit believed percept by percept; the solid line is the
    dopamine pool built from it; the dashed line is the threshold. The circuit
    is usually right and the pool usually never gets there.
    """
    plt = _style()
    config = BrainConfig.from_dict(report["config"])
    verdicts = {v["id"]: v for v in report["unheard_rendition"]["verdicts"]}

    missed = [
        t for t in families["rendition"]
        if t.positive and t.id in verdicts and not verdicts[t.id]["committed"]
    ]
    missed.sort(key=lambda t: -float(t.confidence.max()))
    if not missed:
        return path

    columns = 3
    rows = int(np.ceil(len(missed) / columns))
    fig, axes = plt.subplots(rows, columns, figsize=(4.0 * columns, 2.4 * rows),
                             sharex=False, sharey=True)
    axes = np.atleast_1d(axes).ravel()

    for ax, trace in zip(axes, missed, strict=False):
        dopamine, _ = pool_of(trace, config)
        ax.plot(trace.t, trace.confidence, color=RENDITION, linewidth=1.0, alpha=0.32,
                zorder=2)
        ax.plot(trace.t, dopamine, color=RENDITION, linewidth=2, zorder=3)
        ax.axhline(config.da_commit, color=UPLOAD, linewidth=1.4,
                   linestyle=(0, (4, 3)), zorder=4)
        ax.set_ylim(0, 1.02)
        ax.set_xlim(0, float(trace.t.max()) if len(trace) else 1.0)
        ax.set_title(f"{trace.group}  ({trace.kind})", fontsize=9.5, loc="left",
                     color=INK, pad=4)
        ax.text(0.985, 0.94, f"peak {trace.confidence.max():.2f}", transform=ax.transAxes,
                fontsize=8.5, color=INK_SOFT, ha="right", va="top")
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
        for side in ("left", "bottom"):
            ax.spines[side].set_color(GRID)

    for ax in axes[len(missed):]:
        ax.set_visible(False)
    for ax in axes[: len(missed)][-columns:]:
        ax.set_xlabel("seconds")
    for ax in axes[: len(missed)][::columns]:
        ax.set_ylabel("level")

    handles = [
        plt.Line2D([], [], color=RENDITION, linewidth=2, label="dopamine pool"),
        plt.Line2D([], [], color=RENDITION, linewidth=1.0, alpha=0.32,
                   label="percept confidence"),
        plt.Line2D([], [], color=UPLOAD, linewidth=1.4, linestyle=(0, (4, 3)),
                   label=f"commit threshold ({config.da_commit:.2f})"),
    ]
    fig.legend(handles=handles, loc="lower center", ncols=3, fontsize=9.5,
               labelcolor=INK, bbox_to_anchor=(0.5, -0.015))
    fig.suptitle(
        f"The evidence was there: {len(missed)} held-out positives the fly never called",
        fontsize=12.5, fontweight="bold", x=0.009, ha="left", y=1.005,
    )
    fig.text(
        0.009, 0.978,
        "Every one of these peaks well above one half. The circuit recognised the song; "
        "the accumulator never crossed.",
        fontsize=9.5, color=INK_SOFT, ha="left", va="top",
    )
    fig.tight_layout(rect=(0, 0.015, 1, 0.965))
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    return path


# ── the text the figures are supposed to support ─────────────────────────────


def summarise(report: dict, families: dict[str, list[Trace]]) -> str:
    lines: list[str] = []
    for name, key in (("unheard rendition", "unheard_rendition"),
                      ("unheard upload", "unheard_upload")):
        block = report[key]
        p, t = block["percepts"], block["tracks"]
        lines.append(
            f"{name:18s} macro auc {block['macro_auc']:.4f}  percept auc {p['auc']:.4f}  "
            f"track recall {t['recall']:.3f}  specificity {t['specificity']:.3f}"
        )
    verdicts = report["unheard_rendition"]["verdicts"]
    missed = [v for v in verdicts if v["positive"] and not v["committed"]]
    false = [v for v in verdicts if not v["positive"] and v["committed"]]
    if missed:
        peak = np.mean([v["peak_confidence"] for v in missed])
        lines.append(
            f"\n{len(missed)} missed positives, mean peak confidence {peak:.2f} -- the "
            f"circuit saw them; the commit rule did not fire."
        )
    for v in false:
        lines.append(
            f"  false positive  {v['group']:22s} at {v['latency']:.1f}s  {v['title'][:44]}"
        )
    total = sum(len(t) for fam in families.values() for t in fam)
    lines.append(f"\n{total} out-of-fold percepts across {sum(map(len, families.values()))} traces")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Plot what cross-validation found.")
    parser.add_argument("--metrics", type=Path, default=METRICS_PATH)
    parser.add_argument("--traces", type=Path, default=TRACES_PATH)
    parser.add_argument("--out", type=Path, default=IMG_DIR)
    args = parser.parse_args(argv)

    for path, what in ((args.metrics, "metrics"), (args.traces, "traces")):
        if not path.exists():
            raise SystemExit(f"no {what} at {path}; run 'frrf-train' first")

    report = json.loads(args.metrics.read_text())
    families = load_traces(args.traces)
    args.out.mkdir(parents=True, exist_ok=True)

    print(summarise(report, families))
    print()
    for name, draw in (
        ("roc", lambda p: figure_roc(families, report, p)),
        ("folds", lambda p: figure_folds(report, p)),
        ("commitment", lambda p: figure_commitment(report, p)),
        ("misses", lambda p: figure_misses(families, report, p)),
    ):
        path = draw(args.out / f"{name}.png")
        print(f"drew {path.relative_to(ROOT)} ({path.stat().st_size / 1024:.0f} kB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
