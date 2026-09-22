"""Turn hand-marked spans into percepts the trainer can read.

`data/corrections.jsonl` fills up as people use the application: a video the
fly met in the wild, the seconds where the song actually is, and which way it
was wrong. That is the most useful label this project can get, because it is
out of distribution by definition -- nobody bothers to correct a case the fly
already handles.

This closes the loop. Each correction becomes one cached percept file with the
right label, written into the ordinary feature directory under its own id, and
a merged manifest is written beside it so the trainer can pick them up without
knowing they came from anywhere unusual:

    frrf-corrections
    frrf-train --manifest data/manifest-with-corrections.json

Each correction is its own fold group. A span cut from a video must never end
up in training while another span of the same video is being held out, and
grouping by video id is what stops that.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from api.services import sources
from api.services.corrections import CORRECTIONS_PATH, load
from api.services.media import fetch_audio
from brain.audio import decode, level
from brain.config import BrainConfig
from brain.model import FlyBrain
from training.corpus import FEATURE_DIR, MANIFEST, ROOT
from training.fetch import TRAINING_HOP_FRAMES

CACHE_DIR = ROOT / "data" / "cache"
MERGED_MANIFEST = ROOT / "data" / "manifest-with-corrections.json"

MIN_SECONDS = 1.5
"""Shorter than this and a span cannot fill even one percept window, so it
would contribute nothing but a label."""


def _group(correction: dict) -> str:
    """The fold group a correction belongs to.

    Keyed on the video it was cut from, and on the platform as well, because
    the id spaces overlap: an eleven-digit TikTok id is a well-formed YouTube
    id. Two unrelated videos sharing a group would put one in training while
    the other was held out and call the result a held-out score.
    """
    key = correction.get("source") or sources.DEFAULT_SOURCE.key
    return f"fix-{key}-{correction['video_id']}"


def featurise(
    correction: dict,
    ear,
    config: BrainConfig,
    feature_dir: Path,
    cache_dir: Path,
    force: bool = False,
) -> tuple[str, int] | None:
    """One correction to one cached percept file. Returns (id, percepts)."""
    span = float(correction["end"]) - float(correction["start"])
    if span < MIN_SECONDS:
        return None

    identifier = f"fix-{correction['id']}"
    destination = feature_dir / f"{identifier}.npz"
    if destination.exists() and not force:
        with np.load(destination, allow_pickle=False) as data:
            return identifier, int(len(data["receptors"]))

    source = sources.by_key(correction.get("source") or sources.DEFAULT_SOURCE.key)
    path, _ = fetch_audio(source, correction["video_id"], cache_dir)
    samples = decode(path, config.sample_rate)
    start = int(float(correction["start"]) * config.sample_rate)
    stop = min(len(samples), int(float(correction["end"]) * config.sample_rate))
    clip = samples[start:stop]
    if clip.size < config.n_fft:
        return None

    receptors, t = ear.percepts(
        level(clip, config.target_rms), hop_frames=TRAINING_HOP_FRAMES
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        destination,
        receptors=receptors,
        t=t,
        video_id=np.array(identifier),
        label=np.array(correction["label"]),
        group=np.array(_group(correction)),
        seconds=np.float32(clip.size / config.sample_rate),
        truncated=np.bool_(False),
    )
    return identifier, int(len(receptors))


def merge_manifest(rows: list[dict], manifest_path: Path, out: Path) -> Path:
    """The corpus plus the corrections, in the shape the trainer already reads."""
    manifest = json.loads(manifest_path.read_text())
    known = {track["id"] for track in manifest["tracks"]}
    added = [row for row in rows if row["id"] not in known]
    manifest["tracks"] = manifest["tracks"] + added
    manifest["corrections"] = {
        "count": len(added),
        "note": (
            "Spans marked by hand in the application and folded in by "
            "frrf-corrections. Each is its own fold group, keyed on the video "
            "it was cut from."
        ),
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(manifest, indent=2) + "\n")
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--corrections", type=Path, default=CORRECTIONS_PATH)
    parser.add_argument("--features", type=Path, default=FEATURE_DIR)
    parser.add_argument("--cache", type=Path, default=CACHE_DIR)
    parser.add_argument("--manifest", type=Path, default=MANIFEST)
    parser.add_argument("--out", type=Path, default=MERGED_MANIFEST)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args(argv)

    rows = load(args.corrections)
    if not rows:
        print(f"no corrections in {args.corrections}")
        return 0

    fly = FlyBrain.load(ROOT / "models" / "fly_brain.npz")
    print(f"{len(rows)} corrections")

    tracks, total, skipped = [], 0, 0
    for correction in rows:
        try:
            made = featurise(
                correction, fly.ear, fly.config, args.features, args.cache, args.force
            )
        except Exception as error:
            print(f"  {correction['id']}  FAILED  {type(error).__name__}: {error}")
            skipped += 1
            continue
        if made is None:
            skipped += 1
            continue
        identifier, count = made
        total += count
        tracks.append({
            "id": identifier,
            "source": correction.get("source") or sources.DEFAULT_SOURCE.key,
            "label": correction["label"].replace("not-rickroll", "other"),
            "group": _group(correction),
            "kind": "correction",
            "use": "train",
            "title": (
                f"{correction.get('title') or correction['video_id']} "
                f"[{correction['start']:.1f}-{correction['end']:.1f}s]"
            ),
        })
        print(f"  {identifier}  {count:4d} percepts  {tracks[-1]['title'][:52]}")

    if not tracks:
        print("nothing usable")
        return 1

    written = merge_manifest(tracks, args.manifest, args.out)
    print(f"\n{len(tracks)} corrections featurised, {total} percepts, {skipped} skipped")
    print(f"wrote {written}")
    print(f"train on them with:\n    frrf-train --manifest {written}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
