"""The input field takes YouTube links and nothing else."""

import pytest

from api.services import youtube
from api.services.youtube import NotYouTube, video_id

ID = "dQw4w9WgXcQ"


@pytest.mark.parametrize(
    "url",
    [
        f"https://www.youtube.com/watch?v={ID}",
        f"http://youtube.com/watch?v={ID}",
        f"https://m.youtube.com/watch?v={ID}&list=PL1&index=2",
        f"https://music.youtube.com/watch?v={ID}",
        f"https://youtu.be/{ID}",
        f"https://youtu.be/{ID}?t=43",
        f"https://www.youtube.com/shorts/{ID}",
        f"https://www.youtube.com/embed/{ID}",
        f"https://www.youtube.com/v/{ID}",
        f"https://www.youtube.com/live/{ID}",
        f"  www.youtube.com/watch?v={ID}  ",
    ],
)
def test_accepts_every_shape_of_youtube_link(url):
    assert video_id(url) == ID


@pytest.mark.parametrize(
    "url",
    [
        "",
        "   ",
        "not a url",
        "https://vimeo.com/76979871",
        f"https://notyoutube.com/watch?v={ID}",
        # The lookalike host: youtube.com is a label, not the domain.
        f"https://www.youtube.com.example.test/watch?v={ID}",
        f"file:///etc/passwd?v={ID}",
        f"javascript:alert(1)//youtube.com/watch?v={ID}",
        "https://www.youtube.com/",
        "https://www.youtube.com/@rickastley",
        "https://www.youtube.com/watch?v=tooshort",
        "https://www.youtube.com/watch?v=waaaaaaaaaaytoolong",
        "https://www.youtube.com/watch",
    ],
)
def test_refuses_everything_else(url):
    with pytest.raises(NotYouTube):
        video_id(url)


def test_the_refusal_says_something_useful():
    with pytest.raises(NotYouTube, match="YouTube"):
        video_id("https://vimeo.com/76979871")


# ── link shorteners ─────────────────────────────────────────────────────────
# A Rickroll is very often hidden behind one, so refusing them outright would
# refuse the archetypal case. The rule after the redirect is the rule before
# it, and the hop-by-hop check is what stops this being a way to make the
# server fetch arbitrary addresses.


@pytest.mark.parametrize(
    "url",
    ["https://bit.ly/abc123", "bit.ly/abc123", "https://t.co/xyz", "https://tinyurl.com/q"],
)
def test_known_shorteners_are_recognised(url):
    assert youtube.is_shortener(url)


@pytest.mark.parametrize(
    "url",
    ["https://www.youtube.com/watch?v=dQw4w9WgXcQ", "https://youtu.be/dQw4w9WgXcQ",
     "https://example.com/abc", "https://evil.example/bit.ly/abc"],
)
def test_other_hosts_are_not_shorteners(url):
    assert not youtube.is_shortener(url)


def test_a_shortener_that_lands_on_youtube_resolves(monkeypatch):
    monkeypatch.setattr(youtube, "resolve", lambda url, **kw: "https://youtu.be/dQw4w9WgXcQ")
    assert youtube.resolve_video_id("https://bit.ly/rick") == "dQw4w9WgXcQ"


def test_a_shortener_that_lands_anywhere_else_is_refused(monkeypatch):
    def lands_elsewhere(url, **kw):
        raise youtube.NotYouTube("That link does not lead to YouTube.")

    monkeypatch.setattr(youtube, "resolve", lands_elsewhere)
    with pytest.raises(youtube.NotYouTube):
        youtube.resolve_video_id("https://bit.ly/not-rick")


def test_resolving_refuses_to_wander_off_the_allow_list():
    """The check happens between hops, so a shortener pointing at an internal
    address is refused without the address ever being fetched."""
    for destination in ("http://127.0.0.1:8000/admin", "file:///etc/passwd",
                        "https://169.254.169.254/latest/meta-data"):
        with pytest.raises(youtube.NotYouTube):
            youtube.resolve(destination)


def test_a_direct_link_is_never_followed(monkeypatch):
    def explode(*args, **kwargs):
        raise AssertionError("a direct YouTube link must not touch the network")

    monkeypatch.setattr(youtube.urllib.request, "build_opener", explode)
    assert youtube.resolve_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
