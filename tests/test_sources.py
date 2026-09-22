"""Which links are accepted, and what each one means.

The input field takes a link to one video on a platform we have decided to
accept. That is a product decision rather than an oversight -- the fly is
asked whether a *video* is a Rickroll, and a Rickroll is a link you were
tricked into clicking -- and this is where the decision is enforced.
"""

import pytest

from api.services import sources
from api.services.sources import UnsupportedLink, find

YT = "dQw4w9WgXcQ"
TT = "7680224173913885974"
IG = "C8xYzAbCdEf"


# ── YouTube ──────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "url",
    [
        f"https://www.youtube.com/watch?v={YT}",
        f"http://youtube.com/watch?v={YT}",
        f"https://m.youtube.com/watch?v={YT}&list=PL1&index=2",
        f"https://music.youtube.com/watch?v={YT}",
        f"https://youtu.be/{YT}",
        f"https://youtu.be/{YT}?t=43",
        f"https://www.youtube.com/shorts/{YT}",
        f"https://www.youtube.com/embed/{YT}",
        f"https://www.youtube.com/v/{YT}",
        f"https://www.youtube.com/live/{YT}",
        f"  www.youtube.com/watch?v={YT}  ",
    ],
)
def test_accepts_every_shape_of_youtube_link(url):
    source, identifier = find(url)
    assert (source.key, identifier) == ("youtube", YT)


# ── TikTok ───────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "url",
    [
        f"https://www.tiktok.com/@rickastleyofficial/video/{TT}",
        f"https://tiktok.com/@someone/video/{TT}",
        f"https://www.tiktok.com/@someone/video/{TT}?is_from_webapp=1&sender_device=pc",
        f"https://m.tiktok.com/v/{TT}.html",
        f"  www.tiktok.com/@someone/video/{TT}  ",
    ],
)
def test_accepts_every_shape_of_tiktok_link(url):
    source, identifier = find(url)
    assert (source.key, identifier) == ("tiktok", TT)


def test_a_tiktok_profile_is_not_a_video():
    with pytest.raises(UnsupportedLink, match="not to a single video"):
        find("https://www.tiktok.com/@rickastleyofficial")


# ── Instagram ────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "url",
    [
        f"https://www.instagram.com/p/{IG}/",
        f"https://instagram.com/reel/{IG}/",
        f"https://www.instagram.com/reels/{IG}/",
        f"https://www.instagram.com/tv/{IG}/",
        f"https://www.instagram.com/rickastley/reel/{IG}/",
        f"https://www.instagram.com/p/{IG}/?igsh=abc123",
    ],
)
def test_accepts_every_shape_of_instagram_link(url):
    source, identifier = find(url)
    assert (source.key, identifier) == ("instagram", IG)


def test_an_instagram_profile_is_not_a_video():
    with pytest.raises(UnsupportedLink, match="not to a single video"):
        find("https://www.instagram.com/rickastley/")


# ── everything else ──────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "url",
    [
        "",
        "   ",
        "not a url",
        "https://vimeo.com/76979871",
        f"https://notyoutube.com/watch?v={YT}",
        # The lookalike host: youtube.com is a label, not the domain.
        f"https://www.youtube.com.example.test/watch?v={YT}",
        f"https://www.tiktok.com.example.test/@x/video/{TT}",
        f"https://instagram.com.example.test/p/{IG}/",
        f"file:///etc/passwd?v={YT}",
        f"javascript:alert(1)//youtube.com/watch?v={YT}",
        "https://www.youtube.com/",
        "https://www.youtube.com/@rickastley",
        "https://www.youtube.com/watch?v=tooshort",
        "https://www.youtube.com/watch?v=waaaaaaaaaaytoolong",
        "https://www.youtube.com/watch",
        "https://www.tiktok.com/@someone/video/notanumber",
        "https://www.tiktok.com/@someone/photo/7680224173913885974",
    ],
)
def test_refuses_everything_else(url):
    with pytest.raises(UnsupportedLink):
        find(url)


def test_the_refusal_names_what_is_accepted():
    with pytest.raises(UnsupportedLink, match="YouTube, TikTok and Instagram"):
        find("https://vimeo.com/76979871")


def test_the_id_spaces_overlap_so_the_cache_namespaces_them():
    """An eleven-digit TikTok id is a well-formed YouTube id. Unprefixed, one
    could be served from the other's cached file."""
    collide = "12345678901"
    assert sources.YOUTUBE.id_pattern.match(collide)
    assert sources.TIKTOK.id_pattern.match(collide)
    assert sources.YOUTUBE.cache_stem(collide) != sources.TIKTOK.cache_stem(collide)


# ── links that have to be followed ───────────────────────────────────────────
# A Rickroll is very often hidden behind one, so refusing them outright would
# refuse the archetypal case. The rule after the redirect is the rule before
# it, and the hop-by-hop check is what stops this being a way to make the
# server fetch arbitrary addresses.


@pytest.mark.parametrize(
    "url",
    [
        "https://bit.ly/abc123", "bit.ly/abc123", "https://t.co/xyz",
        "https://tinyurl.com/q",
        # Each platform's own share link, which carries no readable id.
        "https://vm.tiktok.com/ZMabcdef/",
        "https://vt.tiktok.com/ZSabcdef/",
        "https://www.tiktok.com/t/ZTabcdef/",
        "https://www.instagram.com/share/abcdefg/",
    ],
)
def test_links_that_have_to_be_followed_are_recognised(url):
    assert sources.needs_resolving(url)


@pytest.mark.parametrize(
    "url",
    [
        f"https://www.youtube.com/watch?v={YT}",
        f"https://youtu.be/{YT}",
        f"https://www.tiktok.com/@someone/video/{TT}",
        f"https://www.instagram.com/reel/{IG}/",
        "https://example.com/abc",
        "https://evil.example/bit.ly/abc",
    ],
)
def test_a_direct_link_does_not_need_following(url):
    assert not sources.needs_resolving(url)


@pytest.mark.parametrize(
    ("landing", "key", "identifier"),
    [
        (f"https://youtu.be/{YT}", "youtube", YT),
        (f"https://www.tiktok.com/@someone/video/{TT}", "tiktok", TT),
        (f"https://www.instagram.com/reel/{IG}/", "instagram", IG),
    ],
)
def test_a_redirect_that_lands_on_a_source_resolves(monkeypatch, landing, key, identifier):
    monkeypatch.setattr(sources, "resolve", lambda url, **kw: landing)
    source, found = sources.resolve_link("https://bit.ly/rick")
    assert (source.key, found) == (key, identifier)


def test_a_redirect_that_lands_anywhere_else_is_refused(monkeypatch):
    def lands_elsewhere(url, **kw):
        raise UnsupportedLink("That link does not lead anywhere we accept.")

    monkeypatch.setattr(sources, "resolve", lands_elsewhere)
    with pytest.raises(UnsupportedLink):
        sources.resolve_link("https://bit.ly/not-rick")


def test_resolving_refuses_to_wander_off_the_allow_list():
    """The check happens between hops, so a shortener pointing at an internal
    address is refused without the address ever being fetched."""
    for destination in ("http://127.0.0.1:8000/admin", "file:///etc/passwd",
                        "https://169.254.169.254/latest/meta-data"):
        with pytest.raises(UnsupportedLink):
            sources.resolve(destination)


@pytest.mark.parametrize(
    "url",
    [
        f"https://www.youtube.com/watch?v={YT}",
        f"https://www.tiktok.com/@someone/video/{TT}",
        f"https://www.instagram.com/p/{IG}/",
    ],
)
def test_a_direct_link_is_never_followed(monkeypatch, url):
    def explode(*args, **kwargs):
        raise AssertionError("a direct link must not touch the network")

    monkeypatch.setattr(sources.urllib.request, "build_opener", explode)
    assert sources.resolve_link(url)
