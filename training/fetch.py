"""Fetch the corpus and turn it into percepts.

Audio is downloaded once and cached, then run through the ear once and cached
again. Neither cache is committed: the audio is not ours to redistribute, and
the percepts are a deterministic function of it.

Training uses a coarser percept hop than listening does. At inference the fly
updates eight times a second because the interface should feel alive; for
learning that is mostly redundant neighbouring windows, so the hop is doubled
and the corpus halves with no measurable loss.
"""

from __future__ import annotations

import argparse
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np

from brain.audio import JohnstonsOrgan, decode, level
from brain.config import BrainConfig
from training.corpus import AUDIO_DIR, FEATURE_DIR, MAX_TRACK_SECONDS, Manifest, Track

TRAINING_HOP_FRAMES = 22
"""255 ms between training percepts, against 128 ms at inference."""

_FORMAT = "bestaudio[abr<=160]/bestaudio/best"


class FetchError(RuntimeError):
    pass


def download(track: Track, directory: Path = AUDIO_DIR, force: bool = False) -> Path:
    """Pull one track's audio, leaving the codec exactly as YouTube served it."""
    import yt_dlp

    directory.mkdir(parents=True, exist_ok=True)
    existing = sorted(directory.glob(f"{track.id}.*"))
    if existing and not force:
        return existing[0]

    options = {
        "format": _FORMAT,
        "outtmpl": str(directory / "%(id)s.%(ext)s"),
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
        "retries": 3,
        "overwrites": force,
    }
    with yt_dlp.YoutubeDL(options) as ydl:
        try:
            ydl.download([track.watch_url])
        except Exception as error:  # yt-dlp raises a wide family
            raise FetchError(f"{track.id}: {error}") from error

    produced = sorted(directory.glob(f"{track.id}.*"))
    if not produced:
        raise FetchError(f"{track.id}: yt-dlp wrote nothing")
    return produced[0]


def featurise(
    track: Track,
    ear: JohnstonsOrgan,
    audio_dir: Path = AUDIO_DIR,
    feature_dir: Path = FEATURE_DIR,
    force: bool = False,
) -> Path:
    """Decode, truncate, and store one track's percepts."""
    destination = track.feature_path(feature_dir)
    if destination.exists() and not force:
        return destination

    config = ear.config
    samples = decode(track.audio_path(audio_dir), config.sample_rate)
    limit = int(MAX_TRACK_SECONDS * config.sample_rate)
    truncated = samples.size > limit
    if truncated:
        samples = samples[:limit]

    receptors, t = ear.percepts(level(samples, config.target_rms), hop_frames=TRAINING_HOP_FRAMES)
    destination.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        destination,
        receptors=receptors,
        t=t,
        video_id=np.array(track.id),
        label=np.array(track.label),
        group=np.array(track.group),
        seconds=np.float32(samples.size / config.sample_rate),
        truncated=np.bool_(truncated),
    )
    return destination


def _one(
    track: Track, ear: JohnstonsOrgan, force: bool, refeaturise: bool
) -> tuple[Track, str | None]:
    try:
        download(track, force=force)
        featurise(track, ear, force=force or refeaturise)
    except Exception as error:
        return track, str(error)
    return track, None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Download the corpus and cache its percepts.")
    parser.add_argument("--workers", type=int, default=4, help="parallel downloads")
    parser.add_argument("--force", action="store_true", help="re-download and re-featurise")
    parser.add_argument(
        "--refeaturise",
        action="store_true",
        help="rebuild percepts from the audio already on disk, after an ear change",
    )
    parser.add_argument("--only", nargs="*", help="restrict to these video ids")
    args = parser.parse_args(argv)

    manifest = Manifest.load()
    tracks = manifest.tracks
    if args.only:
        wanted = set(args.only)
        tracks = [t for t in tracks if t.id in wanted]

    ear = JohnstonsOrgan(BrainConfig())
    failures: list[tuple[Track, str]] = []
    done = 0

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        worker = lambda t: _one(t, ear, args.force, args.refeaturise)  # noqa: E731
        for track, error in pool.map(worker, tracks):
            done += 1
            if error:
                failures.append((track, error))
                print(f"[{done:3d}/{len(tracks)}] FAILED {track.id}  {error}", file=sys.stderr)
            else:
                print(f"[{done:3d}/{len(tracks)}] {track.label:9s} {track.id}  {track.title}")

    total = 0
    for track in tracks:
        path = track.feature_path()
        if path.exists():
            with np.load(path) as data:
                total += int(data["receptors"].shape[0])
    print(f"\n{len(tracks) - len(failures)}/{len(tracks)} tracks cached, {total} percepts")
    if failures:
        print(f"{len(failures)} failed; rerun to retry just those", file=sys.stderr)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
