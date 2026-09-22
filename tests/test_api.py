"""The HTTP surface. The pipeline itself needs the network, so it is not here."""

import pytest
from fastapi.testclient import TestClient

from api.main import create_app


@pytest.fixture
def client():
    return TestClient(create_app())


def test_health_reports_a_trained_fly(client):
    body = client.get("/api/health").json()
    assert body["ok"] is True
    assert body["fly"]["target"]


def test_the_model_card_describes_the_circuit(client):
    circuit = client.get("/api/brain").json()["circuit"]
    assert circuit["kenyonCells"] > 0
    assert circuit["activeKenyonCells"] < circuit["kenyonCells"]
    assert circuit["receptors"] == circuit["subframes"] * (
        circuit["melBands"] + circuit["chromaBands"]
    )


def test_the_model_card_carries_out_of_fold_scores(client):
    performance = client.get("/api/brain").json()["performance"]
    assert performance["unheardUpload"]["macroAuc"] > 0.5
    assert performance["unheardRendition"] is not None


def test_metrics_are_served_whole(client):
    body = client.get("/api/brain/metrics").json()
    assert "unheard_upload" in body
    assert "commitment" in body


@pytest.mark.parametrize(
    "url", ["https://vimeo.com/76979871", "not a link", "https://www.youtube.com/@rickastley"]
)
def test_a_non_youtube_link_is_refused_before_any_fetch(client, url):
    response = client.post("/api/analysis", json={"url": url})
    assert response.status_code == 400
    assert "detail" in response.json()


def test_an_empty_url_fails_validation(client):
    assert client.post("/api/analysis", json={"url": ""}).status_code == 422


def test_an_absurdly_long_url_fails_validation(client):
    assert client.post("/api/analysis", json={"url": "x" * 5000}).status_code == 422


def test_an_unknown_job_is_a_404(client):
    assert client.get("/api/analysis/deadbeef").status_code == 404
    assert client.get("/api/analysis/deadbeef/events").status_code == 404


def test_the_build_directory_is_served_whole(client, tmp_path, monkeypatch):
    """Not just /assets. The meshes and the favicon live at the build root, and
    mounting only /assets left every one of them a 404."""
    import api.main as main

    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text("<!doctype html><title>fly</title>")
    (dist / "assets" / "app.js").write_text("// bundle")
    (dist / "fly-brain.glb").write_bytes(b"glTF-ish")
    (dist / "favicon.svg").write_text("<svg/>")
    monkeypatch.setattr(main, "WEB_DIST", dist)

    served = TestClient(main.create_app())
    assert served.get("/").status_code == 200
    assert served.get("/assets/app.js").status_code == 200
    assert served.get("/fly-brain.glb").content == b"glTF-ish"
    assert served.get("/favicon.svg").status_code == 200
    # The API still outranks the mount.
    assert served.get("/api/health").json()["ok"] is True


def test_a_shortener_is_accepted_and_resolved_later(client, monkeypatch):
    """It cannot be judged without following it, and following it needs the
    network, so it is admitted here and refused in the worker if it does not
    land on YouTube."""
    import api.routes.analysis as route

    monkeypatch.setattr(route.analysis, "run", lambda job: None)
    response = client.post("/api/analysis", json={"url": "https://bit.ly/whatever"})
    assert response.status_code == 202


def test_media_is_a_404_until_something_has_been_downloaded(client):
    # The job is made through the service rather than the endpoint on purpose:
    # posting would start the real pipeline, and a unit test has no business
    # downloading a video.
    from api.services import analysis as service

    job = service.create("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    assert job.media is None
    assert client.get(f"/api/analysis/{job.id}/media").status_code == 404
    assert client.get("/api/analysis/nope/media").status_code == 404


def test_media_serves_the_downloaded_file(client, tmp_path):
    """The player reads from here rather than from a YouTube embed, because the
    uploads worth asking about are the ones that refuse to embed."""
    from api.services import analysis as service

    job = service.create("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    clip = tmp_path / "clip.mp4"
    clip.write_bytes(b"\x00\x00\x00\x18ftypmp42not-really-a-video")
    job.media = clip

    response = client.get(f"/api/analysis/{job.id}/media")
    assert response.status_code == 200
    assert response.headers["content-type"] == "video/mp4"
    assert response.content == clip.read_bytes()


# ── what a public address is allowed to see ──────────────────────────────────


def test_the_admin_surface_does_not_exist_by_default(client):
    """The workshop starts processes on the host and the notes page writes
    files to it. Off unless asked for, and absent rather than refused: a 403
    tells you where to keep knocking.

    A write verb comes back 405 rather than 404 wherever the frontend has been
    built, because the static mount that catches the path serves GET and HEAD
    and nothing else. Both answers mean the same thing -- there is no such
    route -- so both are accepted.
    """
    gone = {404, 405}
    assert client.get("/api/jobs").status_code in gone
    assert client.post("/api/jobs", json={"job": "train-ear"}).status_code in gone
    assert client.get("/api/models").status_code in gone
    assert client.post("/api/models/active", json={"sense": "ear"}).status_code in gone
    assert client.get("/api/notes").status_code in gone
    assert client.put("/api/notes", json={"text": "hello"}).status_code in gone


def test_the_public_surface_survives_the_gate(client):
    """Everything the interface needs to answer a link is still there."""
    assert client.get("/api/health").status_code == 200
    assert client.get("/api/brain").status_code == 200
    assert client.get("/api/corpus").status_code == 200
    assert client.get("/api/corrections").status_code == 200


def test_the_schema_is_not_published_by_default(client):
    """It is a map of the admin surface."""
    assert client.get("/openapi.json").status_code == 404
    assert client.get("/docs").status_code == 404


def test_developing_publishes_the_schema(monkeypatch):
    monkeypatch.setenv("FRRF_DEV", "1")
    developing = TestClient(create_app())
    assert developing.get("/openapi.json").status_code == 200


def test_a_flood_of_submissions_is_refused(client, monkeypatch):
    """Each submission makes this server talk to YouTube and burn a core."""
    from api import ratelimit

    monkeypatch.setenv("FRRF_RATE_PER_MINUTE", "3")
    ratelimit.reset()
    bad = {"url": "https://vimeo.com/76979871"}
    codes = [client.post("/api/analysis", json=bad).status_code for _ in range(5)]
    assert codes[:3] == [400, 400, 400], codes
    assert codes[3:] == [429, 429], codes
    ratelimit.reset()
