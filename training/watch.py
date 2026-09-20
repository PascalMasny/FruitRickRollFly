"""Fetch the corpus as pictures and turn it into visual percepts.

The twin of `frrf-fetch`, for the eye instead of the ear. It downloads the
worst video YouTube will serve -- which is not a compromise but the right
choice, because 768 ommatidia cannot use more than about 144 lines and asking
for 1080p would mean throwing away 98 percent of every frame after paying to
download it -- and runs it through :class:`brain.eye.Eye`.

The percepts it writes have the same shape and the same timing convention as
the ear's, so `frrf-train --features data/features-eye` trains the same
architecture on sight with no other change.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import numpy as np

from brain.config import BrainConfig
from brain.eye import Eye, frames
from training.corpus import MAX_TRACK_SECONDS, ROOT, Manifest, Track
from training.fetch import FetchError

VIDEO_DIR = ROOT / "data" / "video"
EYE_FEATURE_DIR = ROOT / "data" / "features-eye"

TRAINING_HOP_SECONDS = 0.255
"""255 ms between training percepts, matching the ear's training hop so the two
senses index the same moments."""

VIDEO_FORMAT = "worstvideo[height>=120]/worstvideo/worst"
"""The smallest picture that still has more lines than the fly has facets."""


def download(track: Track, directory: Path = VIDEO_DIR, force: bool = False) -> Path:
    import yt_dlp

    directory.mkdir(parents=True, exist_ok=True)
    existing = sorted(p for p in directory.glob(f"{track.id}.*") if p.suffix != ".part")
    if existing and not force:
        return existing[0]

    options = {
        "format": VIDEO_FORMAT,
        "outtmpl": str(directory / "%(id)s.%(ext)s"),
        "quiet": True, "no_warnings": True, "noprogress": True, "retries": 3,
    }
    with yt_dlp.YoutubeDL(options) as ydl:
        ydl.download([track.watch_url])

    produced = sorted(p for p in directory.glob(f"{track.id}.*") if p.suffix != ".part")
    if not produced:
        raise FetchError(f"{track.id}: yt-dlp wrote no video")
    return produced[0]


def featurise(
    track: Track,
    eye: Eye,
    video_dir: Path = VIDEO_DIR,
    feature_dir: Path = EYE_FEATURE_DIR,
    force: bool = False,
) -> Path:
    destination = feature_dir / f"{track.id}.npz"
    if destination.exists() and not force:
        return destination

    config = eye.config
    pictures = frames(next(iter(sorted(video_dir.glob(f"{track.id}.*")))), config)
    limit = int(MAX_TRACK_SECONDS * config.eye_fps)
    truncated = len(pictures) > limit
    if truncated:
        pictures = pictures[:limit]

    receptors, t = eye.percepts(pictures, hop_seconds=TRAINING_HOP_SECONDS)
    destination.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        destination,
        receptors=receptors,
        t=t,
        video_id=np.array(track.id),
        label=np.array(track.label),
        group=np.array(track.group),
        seconds=np.float32(len(pictures) / config.eye_fps),
        truncated=np.bool_(truncated),
    )
    return destination


def _one(track: Track, eye: Eye, force: bool) -> tuple[str, int]:
    download(track, force=force)
    path = featurise(track, eye, force=force)
    with np.load(path, allow_pickle=False) as data:
        return track.id, int(len(data["receptors"]))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Download the corpus as video and see it.")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--limit", type=int, default=None, help="only the first N tracks")
    args = parser.parse_args(argv)

    manifest = Manifest.load()
    tracks = manifest.trainable()[: args.limit]
    eye = Eye(BrainConfig())
    print(f"{len(tracks)} tracks, {eye.config.eye_columns * eye.config.eye_rows} ommatidia each")

    total, failures = 0, []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(_one, t, eye, args.force): t for t in tracks}
        for done in as_completed(futures):
            track = futures[done]
            try:
                _, count = done.result()
                total += count
                print(f"  {track.id}  {count:5d} percepts  {track.title[:44]}")
            except Exception as error:
                failures.append((track.id, error))
                print(f"  {track.id}  FAILED  {type(error).__name__}: {error}")

    print(f"\n{len(tracks) - len(failures)}/{len(tracks)} tracks seen, {total} percepts")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
