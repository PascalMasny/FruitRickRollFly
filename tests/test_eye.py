"""The visual pathway. Motion, not shapes, and not very much of either."""

import numpy as np
import pytest

from brain.config import BrainConfig
from brain.eye import Eye


@pytest.fixture
def config():
    return BrainConfig()


@pytest.fixture
def eye(config):
    return Eye(config)


def _drift(config, frames=90, speed=1.0, direction="right"):
    """A vertical bar sliding across the eye at a constant speed."""
    rows, columns = config.eye_rows, config.eye_columns
    out = np.zeros((frames, rows, columns), dtype=np.float32)
    for i in range(frames):
        x = (i * speed) % columns
        out[i, :, int(x)] = 1.0
    if direction == "left":
        out = out[:, :, ::-1].copy()
    return out


def test_the_eye_produces_the_ear_s_receptor_count(eye, config):
    """Both senses hand the calyx 180 numbers, so it can read either."""
    receptors, t = eye.percepts(_drift(config))
    assert receptors.shape[1] == config.eye_receptors == config.n_receptors
    assert len(receptors) == len(t)


def test_a_still_image_is_silent(eye, config):
    """A photograph with audio behind it is most of what gets uploaded, and it
    carries no motion at all. It must not be scaled up into looking like it
    does -- which is what per-video normalisation does without a floor."""
    still = np.tile(np.linspace(0, 1, config.eye_rows * config.eye_columns, dtype=np.float32)
                    .reshape(1, config.eye_rows, config.eye_columns), (60, 1, 1))
    receptors, _ = eye.percepts(still)
    assert receptors.max() < 1e-3


def test_noise_on_a_still_image_stays_quiet(eye, config):
    """Compression shimmer is not choreography.

    Stated as a comparison rather than an absolute, because the number that
    matters is how a photograph's noise ranks against something that actually
    moves -- correlators amplify uncorrelated noise a little, and pretending
    otherwise would make the test a lie that happens to pass.
    """
    rng = np.random.default_rng(0)
    base = rng.random((1, config.eye_rows, config.eye_columns), dtype=np.float32)
    shimmer = np.tile(base, (60, 1, 1)) + rng.normal(
        0, 0.002, (60, config.eye_rows, config.eye_columns)
    ).astype(np.float32)

    noisy, _ = eye.percepts(shimmer)
    moving, _ = eye.percepts(_drift(config))
    assert noisy.mean() < moving.mean() / 4


def test_motion_wakes_it_up(eye, config):
    moving, _ = eye.percepts(_drift(config, speed=1.0))
    blank = np.zeros((1, config.eye_rows, config.eye_columns), dtype=np.float32)
    still = np.tile(blank, (90, 1, 1))
    quiet, _ = eye.percepts(still)
    assert moving.mean() > 10 * max(quiet.mean(), 1e-9)


def test_opposite_directions_drive_opposite_channels(eye, config):
    """A correlator is direction-selective, and the two directions are carried
    as two non-negative channels because the calyx cannot read a negative rate.
    Rightward motion must not look like leftward motion."""
    right, _ = eye.percepts(_drift(config, direction="right"))
    left, _ = eye.percepts(_drift(config, direction="left"))
    fields = config.eye_fields_x * config.eye_fields_y
    # First block is horizontal-positive, second is horizontal-negative.
    right_channel = right[:, :fields].mean()
    left_channel = right[:, fields : 2 * fields].mean()
    assert right_channel != pytest.approx(left_channel, rel=0.2)
    assert not np.allclose(right[:, : 2 * fields].mean(0), left[:, : 2 * fields].mean(0))


def test_receptors_are_never_negative(eye, config):
    """The gain control downstream assumes a firing rate."""
    receptors, _ = eye.percepts(_drift(config, speed=2.0))
    assert receptors.min() >= 0.0


def test_a_shorter_hop_gives_more_percepts(eye, config):
    coarse, _ = eye.percepts(_drift(config, frames=200), hop_seconds=0.255)
    fine, _ = eye.percepts(_drift(config, frames=200), hop_seconds=0.128)
    assert len(fine) > len(coarse)
