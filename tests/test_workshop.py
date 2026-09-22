"""Choosing a fly, and starting jobs from a web page without opening a shell."""

import json

import pytest
from fastapi.testclient import TestClient

from api.main import create_app
from api.services import models, trainer


@pytest.fixture
def client():
    return TestClient(create_app())


@pytest.fixture
def shelf(tmp_path, monkeypatch):
    """A models/ directory with one real fly copied into it."""
    import shutil

    from api.services import fly as fly_service

    shelf = tmp_path / "models"
    shelf.mkdir()
    shutil.copy(models.MODEL_DIR / "fly_brain.npz", shelf / "fly_brain.npz")
    shutil.copy(models.MODEL_DIR / "metrics.json", shelf / "metrics.json")
    monkeypatch.setattr(models, "MODEL_DIR", shelf)
    monkeypatch.setattr(models, "CHOICE_PATH", tmp_path / "active-models.json")
    fly_service.forget()
    return shelf


# ── the shelf ────────────────────────────────────────────────────────────────


def test_a_model_describes_itself(shelf):
    found = models.available()
    assert [m.name for m in found] == ["fly_brain.npz"]
    one = found[0]
    # A model with no recorded sense is an ear: there has never been an eye.
    assert one.sense == "ear"
    assert one.kenyon and one.kenyon > 0
    assert one.metrics["upload"]["macroAuc"] > 0.9


def test_the_default_is_used_until_something_is_chosen(shelf):
    assert models.active("ear").name == "fly_brain.npz"
    assert models.active("eye") is None


def test_choosing_survives_a_reread(shelf):
    import shutil

    shutil.copy(shelf / "fly_brain.npz", shelf / "other.npz")
    models.choose("ear", "other.npz")
    assert models.active("ear").name == "other.npz"
    assert json.loads((models.CHOICE_PATH).read_text())["ear"] == "other.npz"
    models.choose("ear", None)
    assert models.active("ear").name == "fly_brain.npz"


def test_a_model_outside_the_shelf_cannot_be_chosen(shelf):
    """The name is a filename, never a path: `choose` must not be a way to
    point the server at an arbitrary file."""
    with pytest.raises(FileNotFoundError):
        models.choose("ear", "../../etc/passwd")
    with pytest.raises(FileNotFoundError):
        models.choose("ear", "nope.npz")


def test_an_unknown_sense_is_refused(shelf):
    with pytest.raises(ValueError):
        models.choose("nose", "fly_brain.npz")


# ── starting jobs ────────────────────────────────────────────────────────────
# The interesting tests here are the ones that never start a process.


def test_every_job_builds_an_argv_without_a_shell():
    for name, job in trainer.JOBS.items():
        argv = job.build({})
        assert isinstance(argv, list) and len(argv) >= 3, name
        assert argv[1] == "-m", name
        assert all(isinstance(part, str) for part in argv), name


@pytest.mark.parametrize(
    "options",
    [
        {"name": "../../etc/passwd"},
        {"name": "models/../../x"},
        {"name": "a b"},
        {"name": ".hidden"},
        {"epochs": 0},
        {"epochs": 10_000},
        {"minSpecificity": 4.0},
    ],
)
def test_bad_options_never_reach_a_command(options):
    with pytest.raises(ValueError):
        trainer.JOBS["train-ear"].build(options)


def test_an_empty_name_falls_back_to_the_default():
    """Empty is "I did not choose", which is different from invalid."""
    assert "models/fly_brain.npz" in trainer.JOBS["train-ear"].build({"name": ""})


def test_the_model_name_stays_inside_models():
    argv = trainer.JOBS["train-ear"].build({"name": "experiment-2"})
    assert "models/experiment-2.npz" in argv
    assert "models/metrics-experiment-2.json" in argv


def test_the_eye_job_trains_on_sight():
    argv = trainer.JOBS["train-eye"].build({})
    assert "--sense" in argv and argv[argv.index("--sense") + 1] == "eye"
    assert "data/features-eye" in argv


def test_corrections_are_opt_in_and_need_a_merged_manifest(tmp_path, monkeypatch):
    monkeypatch.setattr(trainer, "ROOT", tmp_path)
    with pytest.raises(ValueError):
        trainer.JOBS["train-ear"].build({"withCorrections": True})
    assert "--manifest" not in trainer.JOBS["train-ear"].build({})


def test_an_unknown_job_is_a_404(client):
    assert client.post("/api/jobs", json={"job": "rm -rf /"}).status_code == 404


def test_bad_options_are_a_400(client):
    response = client.post(
        "/api/jobs", json={"job": "train-ear", "options": {"name": "../escape"}}
    )
    assert response.status_code == 400


def test_the_job_list_is_served(client):
    body = client.get("/api/jobs").json()
    assert {job["name"] for job in body["jobs"]} >= {"train-ear", "train-eye", "fetch"}


# ── which sense a model answers for ──────────────────────────────────────────


def test_a_recorded_sense_files_the_model_under_it(shelf):
    """`--sense eye` used to be parsed and thrown away, so every eye was filed
    as an ear and could be made the active ear. Both senses produce 180
    receptors, so nothing crashed -- the fly answered with a brain trained on
    motion."""
    from brain.model import FlyBrain

    eye = FlyBrain.load(shelf / "fly_brain.npz")
    eye.metadata = dict(eye.metadata) | {"sense": "eye"}
    eye.save(shelf / "fly_eye.npz")

    by_name = {m.name: m.sense for m in models.available()}
    assert by_name["fly_eye.npz"] == "eye"
    assert by_name["fly_brain.npz"] == "ear"
    # And the one trained on sight must not be offered as the ear's default.
    assert models.active("ear").name == "fly_brain.npz"
    assert models.active("eye").name == "fly_eye.npz"


def test_the_shipped_metadata_records_the_sense():
    from training.train import shipped_metadata

    metadata = shipped_metadata(
        target="a song", sense="eye", epochs=1, seed=0, tracks=2, percepts=3
    )
    assert metadata["sense"] == "eye"
    assert set(metadata) >= {"target", "trained", "sense", "epochs", "seed", "tracks", "percepts"}


# ── the run, and being able to stop it ───────────────────────────────────────


@pytest.fixture
def quiet_shelf(monkeypatch):
    """An empty run table, so a test's process cannot be seen by another."""
    monkeypatch.setattr(trainer, "_RUNS", {})
    monkeypatch.setattr(trainer, "_ORDER", [])


def test_a_run_can_be_stopped_the_instant_it_starts(quiet_shelf, monkeypatch):
    """The Popen used to happen inside the pump thread, so `start` could return
    a run whose process was still None -- and a stop in that window found
    nothing to terminate and reported success anyway."""
    import sys

    monkeypatch.setitem(
        trainer.JOBS, "sleep",
        trainer.Job("sleep", "sleep", "a process that will not end on its own",
                    lambda options: [sys.executable, "-c", "import time; time.sleep(30)"]),
    )
    run = trainer.start("sleep")
    assert run.process is not None, "start returned before the process existed"

    stopped = trainer.stop(run.id)
    assert stopped is not None and stopped.status == "stopped"
    assert run.process.wait(timeout=10) is not None
    assert trainer.current() is None


def test_forgetting_the_fly_drops_the_corpus_summary():
    """The corpus summary is derived from metrics.json and traces.npz, both of
    which a training run rewrites. Cached for the life of the process, the
    training-data tab kept describing the previous fly."""
    from api.services import corpus
    from api.services import fly as fly_service

    corpus.summary()
    assert corpus.summary.cache_info().currsize == 1
    fly_service.forget()
    assert corpus.summary.cache_info().currsize == 0
