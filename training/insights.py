"""Figures and a written walk-through of what the fly was trained on.

`frrf-evaluate` draws what cross-validation *found*. This draws what it was
given, and what it did with each track one by one, because the headline
numbers in the README hide the shape of the corpus and the shape of the
corpus is most of the explanation for them.

Everything here is a function of files already in the repository -- the
manifest, the cached percepts, and the out-of-fold traces -- so it can be
re-run without retraining and without the network.
"""

from __future__ import annotations

import argparse
import collections
import json
from pathlib import Path

import numpy as np

from training.corpus import FEATURE_DIR, ROOT, Manifest, Track
from training.evaluate import (
    INK_FAINT,
    INK_SOFT,
    MUTED,
    RENDITION,
    UPLOAD,
    _frame,
    _style,
)
from training.traces import Trace
from training.traces import load as load_traces

IMG_DIR = ROOT / "docs" / "img"
DOC_PATH = ROOT / "docs" / "TRAINING.md"
TRACES_PATH = ROOT / "models" / "traces.npz"
EYE_TRACES_PATH = ROOT / "models" / "traces-eye.npz"
METRICS_PATH = ROOT / "models" / "metrics.json"


def _percept_counts(tracks: list[Track], directory: Path) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for track in tracks:
        path = track.feature_path(directory)
        if not path.exists():
            continue
        with np.load(path, allow_pickle=False) as data:
            out[track.id] = {
                "percepts": int(len(data["receptors"])),
                "seconds": float(data["seconds"]),
                "truncated": bool(data["truncated"]),
            }
    return out


def figure_corpus(tracks: list[Track], counts: dict[str, dict], path: Path) -> Path:
    """What the fly was given, by kind, in tracks and in percepts.

    The two bars per row disagree on purpose: a kind can be a small number of
    long tracks or a large number of short ones, and the circuit is trained on
    percepts rather than on tracks, so the second bar is the one that decides
    what it learns.
    """
    plt = _style()
    kinds = collections.defaultdict(lambda: {"tracks": 0, "percepts": 0, "positive": False})
    for track in tracks:
        row = kinds[track.kind]
        row["tracks"] += 1
        row["percepts"] += counts.get(track.id, {}).get("percepts", 0)
        row["positive"] = track.is_positive

    order = sorted(kinds.items(), key=lambda kv: (not kv[1]["positive"], -kv[1]["percepts"]))
    labels = [k for k, _ in order]
    y = np.arange(len(order))

    fig, axes = plt.subplots(1, 2, figsize=(9.0, 0.46 * len(order) + 2.4), sharey=True)
    for ax, key, title in (
        (axes[0], "tracks", "tracks"),
        (axes[1], "percepts", "percepts"),
    ):
        values = [row[key] for _, row in order]
        colours = [UPLOAD if row["positive"] else RENDITION for _, row in order]
        ax.barh(y, values, color=colours, height=0.6)
        for i, value in enumerate(values):
            ax.annotate(
                f"{value:,}", xy=(value, i), xytext=(5, 0), textcoords="offset points",
                va="center", fontsize=9, color=INK_SOFT,
            )
        ax.set_xlim(0, max(values) * 1.22)
        _frame(ax, title)
        ax.set_xticks([])
        ax.grid(False)

    axes[0].set_yticks(y, labels)
    axes[0].invert_yaxis()
    fig.suptitle(
        "What the fly was given",
        x=0.012, y=0.99, ha="left", fontsize=13, fontweight="bold",
    )
    fig.text(
        0.012, 0.935,
        f"{len(tracks)} tracks. Orange is the song, blue is everything else. "
        "The circuit trains on percepts,\nso the right-hand bar is the one that "
        "decides what it learns.",
        ha="left", fontsize=9.5, color=INK_SOFT, va="top",
    )
    fig.tight_layout(rect=(0, 0, 1, 0.9))
    fig.savefig(path)
    plt.close(fig)
    return path


def figure_separation(families: dict[str, list[Trace]], path: Path) -> Path:
    """Every track's out-of-fold confidence, as a spread rather than a mean.

    A track is not one number. The interesting cases are the ones whose spread
    crosses the decision -- a positive the fly is mostly unsure about, or a
    negative it is briefly certain of -- and an accuracy figure cannot show
    either of those.
    """
    plt = _style()
    traces = sorted(families["rendition"], key=lambda t: float(np.median(t.confidence)))
    y = np.arange(len(traces))

    fig, ax = plt.subplots(figsize=(8.2, 0.24 * len(traces) + 2.6))
    for i, trace in enumerate(traces):
        colour = UPLOAD if trace.positive else RENDITION
        low, high = np.percentile(trace.confidence, [5, 95])
        ax.plot([low, high], [i, i], color=colour, alpha=0.32, linewidth=2.4,
                solid_capstyle="round")
        ax.plot([float(np.median(trace.confidence))], [i], marker="o", markersize=4.6,
                color=colour, linestyle="")

    ax.axvline(0.5, color=INK_FAINT, linewidth=1.0, linestyle=(0, (4, 3)))
    ax.set_yticks(y, [t.title[:44] for t in traces], fontsize=7.2)
    ax.set_xlim(0, 1)
    ax.set_xlabel("out-of-fold confidence")
    ax.grid(axis="y", visible=False)
    _frame(
        ax,
        "Every track, as a spread",
        "Median dot, 5th to 95th percentile bar. Orange is the song.\n"
        "Read the overlap: that is the whole problem in one picture.",
    )
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    return path


def figure_senses(path: Path) -> Path | None:
    """Sound against sight, on the same folds and the same circuit."""
    if not EYE_TRACES_PATH.exists():
        return None
    plt = _style()
    from training.evaluate import pooled, roc_curve

    fig, ax = plt.subplots(figsize=(6.2, 5.4))
    rows = [
        ("ear, unheard upload", load_traces(TRACES_PATH)["upload"], UPLOAD, "-"),
        ("ear, rendition", load_traces(TRACES_PATH)["rendition"], UPLOAD, (0, (4, 3))),
        ("eye, unheard upload", load_traces(EYE_TRACES_PATH)["upload"], RENDITION, "-"),
        ("eye, rendition", load_traces(EYE_TRACES_PATH)["rendition"], RENDITION, (0, (4, 3))),
    ]
    for label, traces, colour, style in rows:
        score, positive = pooled(traces)
        fpr, tpr = roc_curve(score, positive)
        area = float(np.trapezoid(tpr, fpr))
        ax.plot(fpr, tpr, color=colour, linestyle=style, linewidth=1.9,
                label=f"{label} — {area:.3f}")

    ax.plot([0, 1], [0, 1], color=MUTED, linewidth=1.0)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_xlabel("false positive rate")
    ax.set_ylabel("true positive rate")
    ax.legend(loc="lower right", fontsize=9)
    _frame(
        ax,
        "Hearing it against watching it",
        "Same folds, same circuit, same 180 receptors. Only the sense differs.\n"
        "Sight is barely above the diagonal, which is why no visual fly ships.",
    )
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    return path


def _table(rows: list[tuple], header: tuple) -> str:
    out = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    out += ["| " + " | ".join(str(c) for c in row) + " |" for row in rows]
    return "\n".join(out)


def _thousands(value: int) -> str:
    """1234567 -> "1.234.567". German separators, so the generated document
    reads like the hand-written ones next to it."""
    return f"{value:,}".replace(",", ".")


def write_doc(tracks, counts, families, report, path: Path) -> Path:
    positives = [t for t in tracks if t.is_positive]
    percepts = sum(c["percepts"] for c in counts.values())
    positive_percepts = sum(counts.get(t.id, {}).get("percepts", 0) for t in positives)
    truncated = [t for t in tracks if counts.get(t.id, {}).get("truncated")]
    seconds = sorted(c["seconds"] for c in counts.values())

    kinds = collections.Counter(t.kind for t in tracks)
    groups = collections.Counter(t.group for t in tracks)
    biggest = groups.most_common(5)

    rendition = report["unheard_rendition"]
    upload = report["unheard_upload"]

    def per_kind(kind: str) -> str:
        total = sum(counts.get(t.id, {}).get("percepts", 0) for t in tracks if t.kind == kind)
        return _thousands(total)

    kind_table = _table(
        [
            (
                kind,
                count,
                per_kind(kind),
                "der Song"
                if any(t.is_positive for t in tracks if t.kind == kind)
                else "nicht der Song",
            )
            for kind, count in kinds.most_common()
        ],
        ("Art", "Tracks", "Perzepte", "Label"),
    )

    def row(name: str, block: dict) -> str:
        tracks_block = block["tracks"]
        return (
            f"| {name} | {block['macro_auc']:.3f} macro · "
            f"{block['percepts']['auc']:.3f} gepoolt | {tracks_block['recall']:.3f} | "
            f"{tracks_block['specificity']:.3f} | {tracks_block['median_latency']:.1f} s |"
        )

    score_table = "\n".join([
        "| | Perzept-AUC | Track-Recall | Track-Spezifität | mittlerer Commit |",
        "|---|---|---|---|---|",
        row("unbekannte Darbietung", rendition),
        row("unbekannter Upload", upload),
    ])

    share = f"{positive_percepts / percepts * 100:.0f}"
    span = (
        f"{seconds[0]:.0f} s bis {seconds[-1]:.0f} s, im Mittel "
        f"{seconds[len(seconds) // 2]:.0f} s"
    )
    largest = ", ".join(f"`{g}` ({n})" for g, n in biggest)

    doc = f"""# Worauf die Fliege trainiert wurde

> Die Daten unter dem Argument.

**TL;DR** · Der Korpus in Zahlen und Bildern, erzeugt statt geschrieben. Folds
gehen nach Gruppe und nie nach Track, sonst misst das Ergebnis nichts. Die
Abbildungen zeigen, wo die Fliege unsicher ist, und das ist die Mitte.

Erzeugt von `frrf-insights` aus dem Manifest, den gecachten Perzepten und den
Out-of-Fold-Spuren. Nichts hier braucht das Netz oder ein erneutes Training.

`docs/FINDINGS.md` ist das Argument, das hier sind die Daten darunter.

## Der Korpus

{len(tracks)} Tracks, {_thousands(percepts)} Perzepte, davon
{_thousands(positive_percepts)} ({share} %) der Song. Dieses Ungleichgewicht
wird über Gewichtung behandelt und nicht durch Wegwerfen, jedes negative
Perzept im Korpus wird also gesehen.

![Was die Fliege bekommen hat](img/corpus.png)

{kind_table}

Die Tracklänge reicht von {span}. {len(truncated)} Tracks wurden an der
Längenobergrenze des Korpus abgeschnitten.

**Folds gehen nach Gruppe, nicht nach Track.** Die {len(groups)} Gruppen gibt es,
damit zwei Uploads derselben Aufnahme nie über eine Fold-Grenze getrennt werden
können. Einen Track zurückzuhalten, während sein Zwilling im Training bleibt,
misst nichts. Die größten Gruppen sind {largest}.

## Was sie mit jedem einzelnen macht

![Jeder Track als Streuung](img/separation.png)

Ein Track ist nicht eine Zahl, und die Überlappung in der Mitte dieser Abbildung
ist das ganze Problem: die Fliege liegt bei den Negativen, die sie verfehlt,
nicht selbstbewusst daneben, sie ist *unsicher*, und bei mehreren Positiven ist
sie es auch.

Zwei Zeilen lohnen sich mit dem Auge zu suchen. **She Wants To Dance With Me**
(gleicher Künstler, gleiche Produzenten, gleiches Jahr) sitzt fast ganz oben,
über den meisten echten Positiven. Diese eine Zeile ist das
„sie hat Stock Aitken Waterman, 1987, diese Stimme gelernt"-Problem, das die
README einräumt. Und jede Live-Darbietung und das Klaviercover sitzen in der
unteren Hälfte, was die Darbietungs-Zahl von 0,6 statt 0,97 ist.

## Was die Kreuzvalidierung gefunden hat

{score_table}

![ROC](img/roc.png)

![AUC pro Fold](img/folds.png)

Die Macro-Zahl verdeckt eine breite Streuung, und dafür ist die Fold-Abbildung
da.

## Was die Commit-Regel gekostet hat

![Was die Commit-Regel gekostet hat](img/commitment.png)

## Was sie weiterhin verfehlt

![Fehlschläge](img/misses.png)

## Hören gegen Sehen

![Hören gegen Sehen](img/senses.png)

Derselbe Schaltkreis, dieselben Folds, dieselben 180 Rezeptoren, nur der Sinn
ist anders. Sicht liegt knapp über der Diagonalen, und deshalb weigert sich
`frrf-train`, eine sehende Fliege auszuliefern, und deshalb gibt es kein
`models/fly_eye.npz`. Die Begründung ist Befund 7.

> Erzeugt, nicht geschrieben. `frrf-insights`.
"""
    path.write_text(doc)
    return path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--features", type=Path, default=FEATURE_DIR)
    parser.add_argument("--traces", type=Path, default=TRACES_PATH)
    parser.add_argument("--metrics", type=Path, default=METRICS_PATH)
    parser.add_argument("--img", type=Path, default=IMG_DIR)
    parser.add_argument("--doc", type=Path, default=DOC_PATH)
    args = parser.parse_args(argv)

    tracks = Manifest.load().trainable()
    counts = _percept_counts(tracks, args.features)
    if not counts:
        raise SystemExit(f"no cached percepts in {args.features}; run 'frrf-fetch' first")
    families = load_traces(args.traces)
    report = json.loads(args.metrics.read_text())

    args.img.mkdir(parents=True, exist_ok=True)
    for drawn in (
        figure_corpus(tracks, counts, args.img / "corpus.png"),
        figure_separation(families, args.img / "separation.png"),
        figure_senses(args.img / "senses.png"),
    ):
        if drawn is not None:
            print(f"drew {drawn.relative_to(ROOT)} ({drawn.stat().st_size / 1024:.0f} kB)")

    written = write_doc(tracks, counts, families, report, args.doc)
    print(f"wrote {written.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
