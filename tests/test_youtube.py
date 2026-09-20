"""The input field takes YouTube links and nothing else."""

import pytest

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
