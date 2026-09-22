"""The corpus, and the invariants that make its numbers mean anything.

Two rules govern everything here, and both exist because getting them wrong
produces a number that looks wonderful and says nothing. Split by group, never
by video. And no compilation may be a negative.
"""

import json
from collections import Counter

import pytest

from api.services import sources
from training.corpus import MANIFEST, Manifest, Track


@pytest.fixture(scope="module")
def manifest():
    return Manifest.load()


def test_every_track_names_a_source_we_can_reach(manifest):
    for track in manifest.tracks:
        source = sources.by_key(track.source)
        assert source.id_pattern.match(track.id), f"{track.id} is not a {source.label} id"


def test_a_track_from_another_platform_builds_its_own_watch_url():
    """A TikTok in the corpus has to be fetchable, which means the URL has to be
    that platform's rather than YouTube's with a TikTok id glued on."""
    short = Track(
        id="7680224173913885974", label="rickroll", group="studio-1987",
        kind="short", use="train", title="a message from Rick", source="tiktok",
    )
    assert short.watch_url == "https://www.tiktok.com/@i/video/7680224173913885974"
    assert sources.by_key(short.source).cache_stem(short.id).startswith("tiktok-")


def test_a_track_with_no_source_is_a_youtube_one(manifest):
    """Everything curated before the other platforms were accepted, which is
    all of it, and there is nothing else it could be."""
    assert all(track.source == "youtube" for track in manifest.tracks)


def test_duplicate_ids_are_refused(tmp_path):
    """An id names the cached audio and the cached percepts, so two tracks
    sharing one would train on the same sound twice under two labels."""
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps({
        "target": "x", "curated": "today", "curation_rules": [],
        "tracks": [
            {"id": "dQw4w9WgXcQ", "label": "rickroll", "group": "a",
             "kind": "studio", "use": "train", "title": "one"},
            {"id": "dQw4w9WgXcQ", "label": "other", "group": "b",
             "kind": "studio", "use": "train", "title": "two"},
        ],
    }))
    with pytest.raises(ValueError, match="more than once"):
        Manifest.load(path)


def test_the_master_recording_is_one_group(manifest):
    """Twelve uploads of one 1987 recording. Split those at random and the test
    set is the training set with a different thumbnail -- which is exactly the
    trap a pile of TikToks of the same master would walk back into."""
    studio = [t for t in manifest.tracks if t.group == "studio-1987"]
    assert len(studio) > 1
    assert all(t.label == "rickroll" for t in studio)


def test_no_group_straddles_the_label(manifest):
    """A group is held out whole. One that were both a positive and a negative
    would take its own answer with it."""
    labels = {}
    for track in manifest.tracks:
        labels.setdefault(track.group, set()).add(track.label)
    straddling = {group: sorted(kinds) for group, kinds in labels.items() if len(kinds) > 1}
    assert not straddling, f"these groups carry more than one label: {straddling}"


def test_the_curation_rules_are_written_down():
    """They are the argument for the numbers. A corpus whose rules live only in
    someone's head is a corpus nobody can check."""
    raw = json.loads(MANIFEST.read_text())
    assert len(raw["curation_rules"]) >= 6
    joined = " ".join(raw["curation_rules"]).lower()
    assert "group" in joined and "compilation" in joined
    # The one that a short from another platform is most likely to break.
    assert "tiktok" in joined or "instagram" in joined


def test_the_positive_groups_are_not_one_recording(manifest):
    """Rendition recall is what the corpus is short of. If every positive group
    but one is the same master, there is nothing to generalise from."""
    groups = Counter(t.group for t in manifest.tracks if t.label == "rickroll")
    assert len(groups) >= 8, f"only {len(groups)} distinct positive groups"
