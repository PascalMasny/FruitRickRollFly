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
import subprocess
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import parse_qs, urljoin, urlparse

_HOSTS_WATCH = {
    "youtube.com", "www.youtube.com", "m.youtube.com",
    "music.youtube.com", "www.music.youtube.com",
}
_HOSTS_SHORT = {"youtu.be", "www.youtu.be"}
_HOSTS_SHORTENER = {
    "bit.ly", "tinyurl.com", "t.co", "goo.gl", "ow.ly", "is.gd", "buff.ly",
    "rebrand.ly", "shorturl.at", "cutt.ly", "rb.gy", "tiny.cc", "lnkd.in",
    "trib.al", "dlvr.it", "shorte.st", "bit.do", "s.id", "v.gd",
}
"""Link shorteners we will follow. A Rickroll is very often hidden behind one,
so refusing them outright would refuse the archetypal case -- but the rule
after the redirect is exactly the rule before it: YouTube or nothing."""
VIDEO_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")
"""What a YouTube video id is. Public because every path that accepts one from
outside -- a pasted link, a hand-marked correction -- has to hold it to the
same shape."""
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

    if not VIDEO_ID.match(found):
        raise NotYouTube("No video id in that link.")
    return found


def is_shortener(url: str) -> bool:
    """Whether this is a link we are willing to follow to find a YouTube one."""
    candidate = (url or "").strip()
    if "://" not in candidate:
        candidate = "https://" + candidate
    return (urlparse(candidate).hostname or "").lower() in _HOSTS_SHORTENER


def resolve(url: str, *, timeout: float = 6.0, max_hops: int = 5) -> str:
    """Follow a shortener to whatever it points at, refusing to wander.

    Redirects are followed by hand rather than by urllib, because the check
    that matters happens between hops: every destination must itself be a
    shortener or YouTube. A shortened link that redirects to an internal
    address, a file URL or any other host stops there and is refused, so this
    cannot be pointed at something it should not reach.
    """
    candidate = (url or "").strip()
    if "://" not in candidate:
        candidate = "https://" + candidate

    for _ in range(max_hops):
        parsed = urlparse(candidate)
        host = (parsed.hostname or "").lower()
        if parsed.scheme not in {"http", "https"}:
            raise NotYouTube("Only http and https links are accepted.")
        if host in _HOSTS_WATCH or host in _HOSTS_SHORT:
            return candidate
        if host not in _HOSTS_SHORTENER:
            raise NotYouTube("That link does not lead to YouTube.")

        request = urllib.request.Request(  # noqa: S310 - scheme checked above
            candidate, method="HEAD", headers={"User-Agent": "FruitRickRollFly/0.1"}
        )
        opener = urllib.request.build_opener(_NoRedirect)
        try:
            with opener.open(request, timeout=timeout) as response:
                location = response.headers.get("Location")
                status = response.status
        except urllib.error.HTTPError as error:  # a redirect arrives here
            location = error.headers.get("Location")
            status = error.code
        except Exception as error:
            raise NotYouTube(f"Could not follow that short link: {error}") from error

        if not location or status not in {301, 302, 303, 307, 308}:
            raise NotYouTube("That short link does not lead to YouTube.")
        candidate = urljoin(candidate, location)

    raise NotYouTube("That short link redirects too many times.")


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """Hand every redirect back rather than following it silently."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: D102
        return None


def resolve_video_id(url: str) -> str:
    """The id, following one shortener first if that is what was pasted."""
    if is_shortener(url):
        return video_id(resolve(url))
    return video_id(url)


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


def _options(destination: Path) -> dict:
    return {
        "format": AUDIO_FORMAT,
        "outtmpl": str(destination / "%(id)s.%(ext)s"),
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
        "retries": 3,
        "skip_download": True,
    }


def _describe(identifier: str, info: dict) -> Video:
    return Video(
        id=identifier,
        title=info.get("title") or identifier,
        channel=info.get("uploader") or info.get("channel") or "unknown",
        duration=info.get("duration"),
        thumbnail=info.get("thumbnail"),
    )


def describe(identifier: str, destination: Path) -> Video:
    """Title, channel and duration, without downloading anything."""
    import yt_dlp

    with yt_dlp.YoutubeDL(_options(destination)) as ydl:
        info = ydl.extract_info(f"https://www.youtube.com/watch?v={identifier}", download=False)
    return _describe(identifier, info)


def fetch_audio(identifier: str, destination: Path) -> tuple[Path, Video]:
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
    cached = sorted(destination.glob(f"{identifier}.audio.*"))
    if cached:
        return cached[0], describe(identifier, destination)

    options = _options(destination) | {
        "skip_download": False,
        "format": AUDIO_FORMAT,
        "outtmpl": str(destination / "%(id)s.audio.%(ext)s"),
    }
    with yt_dlp.YoutubeDL(options) as ydl:
        info = ydl.extract_info(f"https://www.youtube.com/watch?v={identifier}", download=True)

    produced = sorted(p for p in destination.glob(f"{identifier}.audio.*") if p.suffix != ".part")
    if not produced:
        raise RuntimeError("YouTube served no audio for that video.")
    return produced[0], _describe(identifier, info)


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


def fetch_media(identifier: str, destination: Path) -> Path:
    """Download the video, or return the copy already on disk."""
    import yt_dlp

    destination.mkdir(parents=True, exist_ok=True)

    def on_disk() -> list[Path]:
        # `.audio.` files are the fly's copy and carry no pictures; matching
        # them here would hand the player a soundtrack and call it a video.
        return sorted(
            p for p in destination.glob(f"{identifier}.*")
            if p.suffix != ".part" and ".audio." not in p.name
        )

    cached = on_disk()
    if cached and has_video_stream(cached[0]):
        return cached[0]
    for stale in cached:
        stale.unlink(missing_ok=True)

    options = _options(destination) | {
        "skip_download": False,
        "format": MEDIA_FORMAT,
        "merge_output_format": "mp4",
    }
    with yt_dlp.YoutubeDL(options) as ydl:
        ydl.download([f"https://www.youtube.com/watch?v={identifier}"])

    produced = on_disk()
    if not produced:
        raise RuntimeError("YouTube served nothing for that video.")
    return produced[0]
