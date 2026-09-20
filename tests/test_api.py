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
