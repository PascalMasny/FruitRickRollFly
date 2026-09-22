"""Getting the sound, and the pictures, off whichever platform it is on.

Nothing here knows what a YouTube link looks like; :mod:`api.services.sources`
does that, and hands this module a source and an id. This is the part that
talks to yt-dlp and ffmpeg, and it is the same work whichever platform the
video came from -- which is the whole reason the two were split apart when
TikTok and Instagram were added.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from api import settings
from api.services.sources import Source


class TooLong(ValueError):
    """The video is longer than this server is willing to listen to."""


class NeedsCredentials(RuntimeError):
    """The platform will not serve this to someone who is not logged in."""


_AUTH_HINTS = ("empty media response", "login required", "rate-limit reached",
               "sign in to confirm", "use --cookies", "requested content is not available")


def _translate(source: Source, error: Exception) -> Exception:
    """Turn yt-dlp's wall of prose into one sentence a person can act on.

    The text is matched rather than the exception type because yt-dlp raises
    the same DownloadError for a missing post, a private one and a blocked
    address range, and only the message tells them apart.
    """
    text = str(error).lower()
    if any(hint in text for hint in _AUTH_HINTS):
        return NeedsCredentials(
            f"{source.label} would not serve that without being logged in. "
            "Set FRRF_COOKIES_FILE to a cookie jar for an account that can see it."
        )
    return error


@dataclass(frozen=True)
class Video:
    id: str
    source: str
    title: str
    channel: str
    duration: float | None
    thumbnail: str | None
    watch_url: str
    embed_url: str | None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "source": self.source,
            "title": self.title,
            "channel": self.channel,
            "duration": self.duration,
            "thumbnail": self.thumbnail,
            "watchUrl": self.watch_url,
            "embedUrl": self.embed_url,
        }


def has_video_stream(path: Path) -> bool:
    """Whether a cached file carries pictures as well as sound.

    Earlier versions downloaded audio only, so the cache can hold files that
    decode perfectly and show nothing.
    """
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=codec_type", "-of", "csv=p=0", str(path)],
        capture_output=True, check=False,
    )
    return probe.returncode == 0 and b"video" in probe.stdout


AUDIO_FORMAT = "bestaudio[abr<=160]/bestaudio/best"
"""What the fly listens to. Small, and the only thing the verdict depends on."""

MEDIA_FORMAT = (
    "bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]"
    "/best[height<=480][ext=mp4]/best[ext=mp4]/best"
)
"""Pictures and sound in one file, capped at 480p.

The player used to be a YouTube embed, and a great many of the videos worth
asking about are exactly the ones whose uploader has disabled embedding -- the
answer was a dead grey box reading *this video is not available*. So the file
is downloaded and served from here instead. ffmpeg decodes whatever container
this lands in, so the same download feeds the fly and the player; H.264 in mp4
because it is the one thing every browser will play.
"""


def _too_long(max_seconds: float | None) -> str:
    minutes = int((max_seconds or 0) // 60)
    return (
        f"That video is longer than the {minutes} minutes this fly will sit through "
        "(or it is a live stream, which has no end to listen to)."
    )


def _options(destination: Path, stem: str, max_seconds: float | None = None) -> dict:
    options = {
        "format": AUDIO_FORMAT,
        "outtmpl": str(destination / f"{stem}.%(ext)s"),
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
        "retries": 3,
        "skip_download": True,
    }
    jar = settings.cookies_file()
    if jar is not None:
        options["cookiefile"] = str(jar)
    if max_seconds and max_seconds > 0:
        from yt_dlp.utils import match_filter_func

        # Judged after extraction and before the download, so an eleven-hour
        # upload costs one metadata call rather than eleven hours of disk. The
        # strict form rejects a video whose duration is unknown, which is what
        # a live stream looks like -- and a live stream has no end to decode.
        options["match_filter"] = match_filter_func(f"duration < {float(max_seconds):.0f}")
    return options


def _describe(source: Source, identifier: str, info: dict) -> Video:
    return Video(
        id=identifier,
        source=source.key,
        title=info.get("title") or identifier,
        channel=info.get("uploader") or info.get("channel") or "unknown",
        duration=info.get("duration"),
        thumbnail=info.get("thumbnail"),
        watch_url=source.watch_url(identifier),
        embed_url=source.embed_url(identifier),
    )


def describe(
    source: Source, identifier: str, destination: Path, max_seconds: float | None = None
) -> Video:
    """Title, channel and duration, without downloading anything."""
    import yt_dlp

    stem = source.cache_stem(identifier)
    try:
        with yt_dlp.YoutubeDL(_options(destination, stem, max_seconds)) as ydl:
            info = ydl.extract_info(source.watch_url(identifier), download=False)
    except Exception as error:
        raise _translate(source, error) from error
    if info is None:
        raise TooLong(_too_long(max_seconds))
    return _describe(source, identifier, info)


def fetch_audio(
    source: Source, identifier: str, destination: Path, max_seconds: float | None = None
) -> tuple[Path, Video]:
    """Download the audio and return it with the metadata, in one round trip.

    Asking yt-dlp for the metadata and then asking it again to download used to
    cost two extractions of the same page -- about 1.5 s of the roughly 4 s a
    cold analysis took, spent entirely on learning a title twice. One call
    downloads and returns the info it had to fetch anyway.

    The audio is named apart from the video because both are cached: the fly
    only ever needs this file, and waiting for the pictures before saying
    anything is what made the answer feel slow.
    """
    import yt_dlp

    destination.mkdir(parents=True, exist_ok=True)
    stem = source.cache_stem(identifier)
    cached = sorted(destination.glob(f"{stem}.audio.*"))
    if cached:
        return cached[0], describe(source, identifier, destination, max_seconds)

    options = _options(destination, f"{stem}.audio", max_seconds) | {"skip_download": False}
    try:
        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(source.watch_url(identifier), download=True)
    except Exception as error:
        raise _translate(source, error) from error
    if info is None:
        raise TooLong(_too_long(max_seconds))

    produced = sorted(p for p in destination.glob(f"{stem}.audio.*") if p.suffix != ".part")
    if not produced:
        raise RuntimeError(f"{source.label} served no audio for that video.")
    return produced[0], _describe(source, identifier, info)


def fetch_media(
    source: Source, identifier: str, destination: Path, max_seconds: float | None = None
) -> Path:
    """Download the video, or return the copy already on disk."""
    import yt_dlp

    destination.mkdir(parents=True, exist_ok=True)
    stem = source.cache_stem(identifier)

    def on_disk() -> list[Path]:
        # `.audio.` files are the fly's copy and carry no pictures; matching
        # them here would hand the player a soundtrack and call it a video.
        return sorted(
            p for p in destination.glob(f"{stem}.*")
            if p.suffix != ".part" and ".audio." not in p.name
        )

    cached = on_disk()
    if cached and has_video_stream(cached[0]):
        return cached[0]
    for stale in cached:
        stale.unlink(missing_ok=True)

    options = _options(destination, stem, max_seconds) | {
        "skip_download": False,
        "format": MEDIA_FORMAT,
        "merge_output_format": "mp4",
    }
    with yt_dlp.YoutubeDL(options) as ydl:
        ydl.download([source.watch_url(identifier)])

    produced = on_disk()
    if not produced:
        raise RuntimeError(f"{source.label} served nothing for that video.")
    return produced[0]
