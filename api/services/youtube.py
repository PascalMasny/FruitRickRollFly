"""Everything that touches YouTube.

The input field takes YouTube links and nothing else. That is a product
decision, not an oversight: the fly is asked whether a *video* is a Rickroll,
and a Rickroll is a link you were tricked into clicking. A bare audio file
would be a different question.

Validation is strict and happens before anything is fetched. A link that is
not YouTube never reaches the network layer.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import parse_qs, urlparse

_HOSTS_WATCH = {
    "youtube.com", "www.youtube.com", "m.youtube.com",
    "music.youtube.com", "www.music.youtube.com",
}
_HOSTS_SHORT = {"youtu.be", "www.youtu.be"}
_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")
_PATH_PREFIXES = ("/shorts/", "/embed/", "/v/", "/live/")


class NotYouTube(ValueError):
    """The link is not a YouTube video link."""


@dataclass(frozen=True)
class Video:
    id: str
    title: str
    channel: str
    duration: float | None
    thumbnail: str | None

    @property
    def watch_url(self) -> str:
        return f"https://www.youtube.com/watch?v={self.id}"

    @property
    def embed_url(self) -> str:
        return f"https://www.youtube-nocookie.com/embed/{self.id}"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "channel": self.channel,
            "duration": self.duration,
            "thumbnail": self.thumbnail,
            "watchUrl": self.watch_url,
            "embedUrl": self.embed_url,
        }


def video_id(url: str) -> str:
    """Pull the video id out of a YouTube link, or refuse the link.

    Accepted: ``youtube.com/watch?v=``, ``youtu.be/``, and the ``/shorts/``,
    ``/embed/``, ``/v/`` and ``/live/`` paths, on the usual hosts, with or
    without a scheme. Everything else raises :class:`NotYouTube`.
    """
    candidate = (url or "").strip()
    if not candidate:
        raise NotYouTube("Paste a YouTube link.")
    if "://" not in candidate:
        candidate = "https://" + candidate

    parsed = urlparse(candidate)
    if parsed.scheme not in {"http", "https"}:
        raise NotYouTube("Only http and https links are accepted.")
    host = (parsed.hostname or "").lower()

    if host in _HOSTS_SHORT:
        found = parsed.path.lstrip("/").split("/")[0]
    elif host in _HOSTS_WATCH:
        if parsed.path in {"/watch", "/watch/"}:
            found = (parse_qs(parsed.query).get("v") or [""])[0]
        elif parsed.path.startswith(_PATH_PREFIXES):
            found = parsed.path.split("/")[2] if len(parsed.path.split("/")) > 2 else ""
        else:
            raise NotYouTube("That is a YouTube link, but not to a single video.")
    else:
        raise NotYouTube("This only takes YouTube links.")

    if not _ID.match(found):
        raise NotYouTube("No video id in that link.")
    return found


def _options(destination: Path) -> dict:
    return {
        "format": "bestaudio[abr<=160]/bestaudio/best",
        "outtmpl": str(destination / "%(id)s.%(ext)s"),
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
        "retries": 3,
        "skip_download": True,
    }


def describe(identifier: str, destination: Path) -> Video:
    """Fetch title, channel and duration without downloading the media."""
    import yt_dlp

    with yt_dlp.YoutubeDL(_options(destination)) as ydl:
        info = ydl.extract_info(f"https://www.youtube.com/watch?v={identifier}", download=False)
    return Video(
        id=identifier,
        title=info.get("title") or identifier,
        channel=info.get("uploader") or info.get("channel") or "unknown",
        duration=info.get("duration"),
        thumbnail=info.get("thumbnail"),
    )


def fetch_audio(identifier: str, destination: Path) -> Path:
    """Download the audio track, or return the copy already on disk."""
    import yt_dlp

    destination.mkdir(parents=True, exist_ok=True)
    cached = sorted(p for p in destination.glob(f"{identifier}.*") if p.suffix != ".part")
    if cached:
        return cached[0]

    options = _options(destination) | {"skip_download": False}
    with yt_dlp.YoutubeDL(options) as ydl:
        ydl.download([f"https://www.youtube.com/watch?v={identifier}"])

    produced = sorted(p for p in destination.glob(f"{identifier}.*") if p.suffix != ".part")
    if not produced:
        raise RuntimeError("YouTube served no audio for that video.")
    return produced[0]
