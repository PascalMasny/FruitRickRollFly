"""Corrections: the labels people add after the fly gets one wrong."""

import json

import pytest
from fastapi.testclient import TestClient

from api.main import create_app
from api.services import corrections


@pytest.fixture
def client():
    return TestClient(create_app())


@pytest.fixture
def log(tmp_path, monkeypatch):
    path = tmp_path / "corrections.jsonl"
    monkeypatch.setattr(corrections, "CORRECTIONS_PATH", path)
    return path


def _span(**over):
    return {
        "videoId": "dQw4w9WgXcQ", "label": "rickroll",
        "start": 11.0, "end": 15.0,
    } | over


# ── what counts as a correction ──────────────────────────────────────────────


def test_a_marked_span_round_trips(log):
    correction = corrections.append(corrections.validate(_span(note="the sting")), log)
    stored = corrections.load(log)
    assert len(stored) == 1
    assert stored[0]["video_id"] == "dQw4w9WgXcQ"
    assert stored[0]["label"] == "rickroll"
    assert stored[0]["note"] == "the sting"
    assert stored[0]["id"] == correction.id


def test_the_log_is_append_only(log):
    """History is the point. A second opinion about a video must not quietly
    replace the first one."""
    for start in (1.0, 2.0, 3.0):
        corrections.append(corrections.validate(_span(start=start, end=start + 2)), log)
    assert [row["start"] for row in corrections.load(log)] == [1.0, 2.0, 3.0]


@pytest.mark.parametrize(
    "bad",
    [
        {"label": "maybe"},
        {"label": ""},
        {"videoId": ""},
        {"start": 5.0, "end": 5.0},
        {"start": 9.0, "end": 3.0},
        {"start": -1.0, "end": 3.0},
        {"start": 0.0, "end": 7200.0},
    ],
)
def test_nonsense_spans_are_refused(bad):
    with pytest.raises(corrections.InvalidCorrection):
        corrections.validate(_span(**bad))


def test_a_malformed_line_does_not_cost_the_whole_log(log, tmp_path):
    corrections.append(corrections.validate(_span()), log)
    with log.open("a", encoding="utf-8") as handle:
        handle.write("{not json at all\n")
    corrections.append(corrections.validate(_span(start=20.0, end=24.0)), log)
    assert len(corrections.load(log)) == 2


# ── over HTTP ────────────────────────────────────────────────────────────────


def test_posting_a_correction_stores_it(client, log):
    created = client.post("/api/corrections", json=_span(title="the record"))
    assert created.status_code == 201
    assert created.json()["label"] == "rickroll"

    listed = client.get("/api/corrections").json()
    assert listed["count"] == 1
    assert listed["corrections"][0]["title"] == "the record"


def test_a_bad_correction_is_a_400(client, log):
    assert client.post("/api/corrections", json=_span(label="sort of")).status_code == 400


def test_notes_round_trip(client, tmp_path, monkeypatch):
    monkeypatch.setattr(corrections, "NOTES_PATH", tmp_path / "notes.md")
    assert client.put("/api/notes", json={"text": "# what I think\n"}).status_code == 200
    assert client.get("/api/notes").json()["text"] == "# what I think\n"


def test_the_corpus_describes_every_track(client):
    body = client.get("/api/corpus").json()
    assert body["tracks"]
    scored = [t for t in body["tracks"] if t["spread"]]
    assert scored, "no track carries an out-of-fold spread"
    one = scored[0]
    assert {"id", "title", "kind", "positive", "watchUrl"} <= set(one)
    assert any(t["positive"] for t in body["tracks"])
    assert any(not t["positive"] for t in body["tracks"])


# ── folding them back into training ──────────────────────────────────────────


def test_each_correction_is_its_own_fold_group(tmp_path):
    """Two spans of one video must never be split across a fold boundary: the
    second would leak the first straight into training."""
    from training.corrections import merge_manifest

    base = tmp_path / "manifest.json"
    base.write_text(json.dumps({"target": "x", "tracks": [
        {"id": "aaa", "label": "rickroll", "group": "studio", "kind": "studio", "use": "train"},
    ]}))
    rows = [
        {"id": "fix-1", "label": "rickroll", "group": "fix-vid", "kind": "correction",
         "use": "train", "title": "a"},
        {"id": "fix-2", "label": "other", "group": "fix-vid", "kind": "correction",
         "use": "train", "title": "b"},
    ]
    merged = json.loads(merge_manifest(rows, base, tmp_path / "merged.json").read_text())
    assert len(merged["tracks"]) == 3
    assert merged["corrections"]["count"] == 2
    groups = {t["group"] for t in merged["tracks"] if t["kind"] == "correction"}
    assert groups == {"fix-vid"}


@pytest.mark.parametrize(
    "identifier",
    ["../../../etc/passwd", "dQw4w9WgXcQ extra", "short", "dQw4w9WgXcQdQw4w9WgXcQ", "../"],
)
def test_a_video_id_that_is_not_one_is_refused(identifier):
    """This endpoint is open and what it stores is read back by
    frrf-corrections, where the id becomes a glob pattern and the tail of a
    fetch URL. Neither has any business taking an arbitrary string."""
    with pytest.raises(corrections.InvalidCorrection):
        corrections.validate(_span(videoId=identifier))


def test_a_bad_video_id_is_a_400(client, log):
    bad = _span(videoId="../../../etc/passwd")
    assert client.post("/api/corrections", json=bad).status_code == 400
    assert corrections.load(log) == []
