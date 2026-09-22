"""The ceilings a public address needs and a laptop does not."""

import time

import pytest

from api import ratelimit, settings
from api.services.cache import sweep


@pytest.fixture(autouse=True)
def clean():
    ratelimit.reset()
    yield
    ratelimit.reset()


# ── settings ─────────────────────────────────────────────────────────────────


def test_the_defaults_are_the_safe_ones(monkeypatch):
    for name in (settings.ADMIN, settings.DEV, settings.ORIGINS):
        monkeypatch.delenv(name, raising=False)
    assert settings.admin() is False
    assert settings.dev() is False
    assert settings.cors_origins() == []
    assert settings.max_video_seconds() > 0
    assert settings.max_concurrent() >= 1


def test_a_setting_is_read_at_call_time(monkeypatch):
    """Captured at import, a value could not be moved back by a test -- or by
    anything else that changes the environment after the module loads."""
    monkeypatch.setenv(settings.ADMIN, "1")
    assert settings.admin() is True
    monkeypatch.setenv(settings.ADMIN, "0")
    assert settings.admin() is False


def test_a_setting_that_is_not_a_number_says_so(monkeypatch):
    monkeypatch.setenv(settings.MAX_VIDEO_SECONDS, "as long as it takes")
    with pytest.raises(ValueError):
        settings.max_video_seconds()


def test_the_dev_server_origin_is_only_allowed_while_developing(monkeypatch):
    monkeypatch.delenv(settings.ORIGINS, raising=False)
    monkeypatch.setenv(settings.DEV, "1")
    assert "http://localhost:5173" in settings.cors_origins()
    monkeypatch.setenv(settings.DEV, "0")
    assert settings.cors_origins() == []


# ── the cache ────────────────────────────────────────────────────────────────


def _file(directory, name, size, age=0.0):
    path = directory / name
    path.write_bytes(b"\0" * size)
    if age:
        when = time.time() - age
        import os

        os.utime(path, (when, when))
    return path


def test_the_oldest_go_first(tmp_path):
    old = _file(tmp_path, "old.mp4", 400, age=900)
    middle = _file(tmp_path, "middle.mp4", 400, age=600)
    recent = _file(tmp_path, "recent.mp4", 400, age=1)

    freed = sweep(tmp_path, budget_bytes=500)
    assert freed >= 700
    assert not old.exists() and not middle.exists()
    assert recent.exists(), "the newest file is the one worth keeping"


def test_a_file_a_live_job_is_serving_is_spared(tmp_path):
    """A cache is allowed to lose things. It is not allowed to lose the file
    another analysis is in the middle of."""
    busy = _file(tmp_path, "busy.mp4", 800, age=9000)
    idle = _file(tmp_path, "idle.mp4", 800, age=1)

    sweep(tmp_path, budget_bytes=100, keep={busy})
    assert busy.exists()
    assert not idle.exists()


def test_a_directory_under_budget_is_left_alone(tmp_path):
    kept = _file(tmp_path, "small.mp4", 10)
    assert sweep(tmp_path, budget_bytes=1_000_000) == 0
    assert kept.exists()


def test_a_budget_of_zero_sweeps_nothing(tmp_path):
    """Zero is the old behaviour, and the reason a laptop quietly accumulated
    95 MB nobody decided to keep."""
    kept = _file(tmp_path, "big.mp4", 5000)
    assert sweep(tmp_path, budget_bytes=0) == 0
    assert kept.exists()


def test_the_gitkeep_survives(tmp_path):
    marker = _file(tmp_path, ".gitkeep", 0, age=9999)
    _file(tmp_path, "big.mp4", 5000, age=9999)
    sweep(tmp_path, budget_bytes=1)
    assert marker.exists(), "the directory has to stay in the repository"


# ── the window ───────────────────────────────────────────────────────────────


def test_a_client_gets_its_allowance_and_no_more():
    assert [ratelimit.allow("a", 3) for _ in range(5)] == [True, True, True, False, False]


def test_clients_are_counted_apart():
    assert all(ratelimit.allow("a", 2) for _ in range(2))
    assert ratelimit.allow("b", 2) is True


def test_the_window_slides():
    now = 1000.0
    assert all(ratelimit.allow("a", 2, now=now + i * 0.1) for i in range(2))
    assert ratelimit.allow("a", 2, now=now + 1.0) is False
    assert ratelimit.allow("a", 2, now=now + ratelimit.WINDOW_SECONDS + 1) is True


def test_a_limit_of_zero_is_no_limit():
    assert all(ratelimit.allow("a", 0) for _ in range(50))


def test_the_table_of_clients_is_itself_bounded():
    """The table is an allocation a caller can drive, so it is swept."""
    for i in range(ratelimit.MAX_TRACKED + 500):
        ratelimit.allow(f"client-{i}", 1, now=1000.0 + ratelimit.WINDOW_SECONDS * 2)
    assert len(ratelimit._HITS) <= ratelimit.MAX_TRACKED + 500
