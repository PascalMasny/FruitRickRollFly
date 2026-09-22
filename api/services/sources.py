"""Which links we accept, and what a link means.

The fly is asked whether a *video* is a Rickroll, and a Rickroll is a link you
were tricked into clicking. Which platforms that covers is a product decision
and it is written down here rather than spread through the fetching code: a
source is a set of hosts, a shape of id, and a way back to a canonical URL.

Validation is strict and happens before anything is fetched. A link that
belongs to no source never reaches the network layer, and the one place that
does touch the network before validating -- following a shortener -- re-checks
every hop against the same rule.
"""

from __future__ import annotations

import re
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from urllib.parse import ParseResult, parse_qs, urljoin, urlparse


class UnsupportedLink(ValueError):
    """The link is not to a video on a platform we accept."""


@dataclass(frozen=True)
class Source:
    """One platform: where its videos live and what its ids look like."""

    key: str
    label: str
    hosts: frozenset[str]
    id_pattern: re.Pattern[str]
    extract: Callable[[ParseResult], str]
    watch_template: str
    embed_template: str | None = None
    redirect_hosts: frozenset[str] = frozenset()
    """Hosts of this platform's own shortener, which must be followed rather
    than parsed."""
    redirect_paths: tuple[str, ...] = ()
    """Paths on a main host that are a redirect rather than a video -- TikTok
    serves its share links from tiktok.com/t/ alongside the real ones."""

    def watch_url(self, identifier: str) -> str:
        return self.watch_template.format(id=identifier)

    def embed_url(self, identifier: str) -> str | None:
        return self.embed_template.format(id=identifier) if self.embed_template else None

    def cache_stem(self, identifier: str) -> str:
        """What this video is called on disk.

        Namespaced by source, because the id spaces overlap: a YouTube id is
        eleven characters of [A-Za-z0-9_-], which an eleven-digit TikTok id
        satisfies exactly. Unprefixed, one could be served for the other.
        """
        return f"{self.key}-{identifier}"


# ── YouTube ──────────────────────────────────────────────────────────────────

_YT_PATH_PREFIXES = ("/shorts/", "/embed/", "/v/", "/live/")


def _youtube_id(parsed: ParseResult) -> str:
    host = (parsed.hostname or "").lower()
    if host in {"youtu.be", "www.youtu.be"}:
        return parsed.path.lstrip("/").split("/")[0]
    if parsed.path in {"/watch", "/watch/"}:
        return (parse_qs(parsed.query).get("v") or [""])[0]
    if parsed.path.startswith(_YT_PATH_PREFIXES):
        parts = parsed.path.split("/")
        return parts[2] if len(parts) > 2 else ""
    return ""


YOUTUBE = Source(
    key="youtube",
    label="YouTube",
    hosts=frozenset({
        "youtube.com", "www.youtube.com", "m.youtube.com",
        "music.youtube.com", "www.music.youtube.com",
        "youtu.be", "www.youtu.be",
    }),
    id_pattern=re.compile(r"^[A-Za-z0-9_-]{11}$"),
    extract=_youtube_id,
    watch_template="https://www.youtube.com/watch?v={id}",
    embed_template="https://www.youtube-nocookie.com/embed/{id}",
)


# ── TikTok ───────────────────────────────────────────────────────────────────


def _tiktok_id(parsed: ParseResult) -> str:
    parts = [part for part in parsed.path.split("/") if part]
    # /@handle/video/<id>, and the photo posts that share the shape but carry
    # no sound worth asking about.
    if len(parts) >= 3 and parts[0].startswith("@") and parts[1] == "video":
        return parts[2]
    # m.tiktok.com/v/<id>.html
    if len(parts) >= 2 and parts[0] == "v":
        return parts[1].removesuffix(".html")
    return ""


TIKTOK = Source(
    key="tiktok",
    label="TikTok",
    hosts=frozenset({"tiktok.com", "www.tiktok.com", "m.tiktok.com"}),
    # Nineteen digits today. Bounded rather than pinned, because the length has
    # grown before and an id is a snowflake rather than a format anyone promised.
    id_pattern=re.compile(r"^\d{6,25}$"),
    extract=_tiktok_id,
    watch_template="https://www.tiktok.com/@i/video/{id}",
    embed_template="https://www.tiktok.com/embed/v2/{id}",
    redirect_hosts=frozenset({"vm.tiktok.com", "vt.tiktok.com"}),
    redirect_paths=("/t/",),
)


# ── Instagram ────────────────────────────────────────────────────────────────

_IG_KINDS = {"p", "reel", "reels", "tv"}


def _instagram_id(parsed: ParseResult) -> str:
    parts = [part for part in parsed.path.split("/") if part]
    # /p/<code>, /reel/<code>, /tv/<code>, and /<handle>/reel/<code>, which is
    # the shape the app's own share button produces.
    for index, part in enumerate(parts[:-1]):
        if part in _IG_KINDS:
            return parts[index + 1]
    return ""


INSTAGRAM = Source(
    key="instagram",
    label="Instagram",
    hosts=frozenset({"instagram.com", "www.instagram.com", "m.instagram.com"}),
    id_pattern=re.compile(r"^[A-Za-z0-9_-]{5,24}$"),
    extract=_instagram_id,
    # /p/ rather than /reel/: yt-dlp reads a post, a reel and an IGTV entry off
    # the same shortcode, and this is the form that works for all three.
    watch_template="https://www.instagram.com/p/{id}/",
    embed_template="https://www.instagram.com/p/{id}/embed/",
    redirect_hosts=frozenset({"instagr.am"}),
    redirect_paths=("/share/",),
)


SOURCES: tuple[Source, ...] = (YOUTUBE, TIKTOK, INSTAGRAM)

DEFAULT_SOURCE = YOUTUBE
"""What a record with no source recorded means. Corrections written before
TikTok was accepted are all YouTube, and there is no other thing they could be."""

_GENERIC_SHORTENERS = frozenset({
    "bit.ly", "tinyurl.com", "t.co", "goo.gl", "ow.ly", "is.gd", "buff.ly",
    "rebrand.ly", "shorturl.at", "cutt.ly", "rb.gy", "tiny.cc", "lnkd.in",
    "trib.al", "dlvr.it", "shorte.st", "bit.do", "s.id", "v.gd",
})
"""Link shorteners we will follow. A Rickroll is very often hidden behind one,
so refusing them outright would refuse the archetypal case -- but the rule
after the redirect is exactly the rule before it."""


def by_key(key: str) -> Source:
    for source in SOURCES:
        if source.key == key:
            return source
    raise UnsupportedLink(f"no such source: {key!r}")


def accepted() -> str:
    """The platforms, as a sentence, for a refusal that is worth reading."""
    labels = [source.label for source in SOURCES]
    return " and ".join([", ".join(labels[:-1]), labels[-1]] if len(labels) > 1 else labels)


def _normalise(url: str) -> str:
    candidate = (url or "").strip()
    if not candidate:
        raise UnsupportedLink(f"Paste a {accepted()} link.")
    if "://" not in candidate:
        candidate = "https://" + candidate
    return candidate


def _parse(url: str) -> ParseResult:
    parsed = urlparse(_normalise(url))
    if parsed.scheme not in {"http", "https"}:
        raise UnsupportedLink("Only http and https links are accepted.")
    return parsed


def source_for(host: str) -> Source | None:
    for source in SOURCES:
        if host in source.hosts:
            return source
    return None


def find(url: str) -> tuple[Source, str]:
    """The platform and the video id, or a refusal.

    Everything a source does not recognise raises :class:`UnsupportedLink`,
    including a link to that platform that is not a link to one video.
    """
    parsed = _parse(url)
    host = (parsed.hostname or "").lower()

    source = source_for(host)
    if source is None:
        raise UnsupportedLink(f"This only takes {accepted()} links.")
    if any(parsed.path.startswith(prefix) for prefix in source.redirect_paths):
        raise UnsupportedLink(f"That {source.label} link has to be followed first.")

    found = source.extract(parsed)
    if not found:
        raise UnsupportedLink(
            f"That is a {source.label} link, but not to a single video."
        )
    if not source.id_pattern.match(found):
        raise UnsupportedLink("No video id in that link.")
    return source, found


def needs_resolving(url: str) -> bool:
    """Whether this link has to be followed before it can be judged.

    A generic shortener, a platform's own share host, or a share path on a
    platform's main host. All three are a redirect and none of them carries an
    id that can be read off the URL.
    """
    try:
        parsed = _parse(url)
    except UnsupportedLink:
        return False
    host = (parsed.hostname or "").lower()
    if host in _GENERIC_SHORTENERS:
        return True
    for source in SOURCES:
        if host in source.redirect_hosts:
            return True
        if host in source.hosts and any(
            parsed.path.startswith(prefix) for prefix in source.redirect_paths
        ):
            return True
    return False


def resolve(url: str, *, timeout: float = 6.0, max_hops: int = 5) -> str:
    """Follow a redirect to whatever it points at, refusing to wander.

    Redirects are followed by hand rather than by urllib, because the check
    that matters happens between hops: every destination must itself be a
    redirect we accept or a video on a source we accept. A link that redirects
    to an internal address, a file URL or any other host stops there and is
    refused, so this cannot be pointed at something it should not reach.
    """
    candidate = _normalise(url)

    for _ in range(max_hops):
        parsed = _parse(candidate)
        host = (parsed.hostname or "").lower()

        # Asked before the host check, because a platform's own share path
        # lives on its main host and is still a redirect.
        if needs_resolving(candidate):
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
                raise UnsupportedLink(f"Could not follow that short link: {error}") from error

            if not location or status not in {301, 302, 303, 307, 308}:
                raise UnsupportedLink(f"That short link does not lead to {accepted()}.")
            candidate = urljoin(candidate, location)
            continue

        if source_for(host) is not None:
            return candidate
        raise UnsupportedLink(f"That link does not lead to {accepted()}.")

    raise UnsupportedLink("That short link redirects too many times.")


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """Hand every redirect back rather than following it silently."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: D102
        return None


def resolve_link(url: str) -> tuple[Source, str]:
    """The source and the id, following one redirect first if that is what
    was pasted."""
    return find(resolve(url) if needs_resolving(url) else url)
