"""The whole fly: encode, learn, persist."""

import numpy as np
import pytest

from brain.model import FlyBrain


@pytest.fixture
def separable(config):
    """Two clearly different sound-like inputs, and their labels."""
    rng = np.random.default_rng(11)
    n = 600
    base = rng.random((n, config.n_receptors), dtype=np.float32)
    target = np.where(np.arange(n) % 2 == 0, 1.0, -1.0).astype(np.float32)
    signature = rng.random(config.n_receptors, dtype=np.float32)
    base[target > 0] += 1.4 * signature
    return base, target


def test_a_naive_fly_has_no_opinion(config, separable):
    receptors, _ = separable
    brain = FlyBrain(config)
    brain.calibrate(receptors)
    assert np.allclose(brain.valence(brain.encode(receptors)), 0.0)


def test_dopamine_teaches_it_the_difference(config, separable):
    receptors, target = separable
    brain = FlyBrain(config)
    brain.calibrate(receptors)
    kenyon = brain.encode(receptors)

    rng = np.random.default_rng(0)
    for _ in range(40):
        brain.learn(kenyon, target, rng=rng)

    valence = brain.valence(kenyon)
    assert valence[target > 0].mean() > valence[target < 0].mean()
    assert float(((valence > 0) == (target > 0)).mean()) > 0.9


def test_learning_reduces_the_prediction_error(config, separable):
    receptors, target = separable
    brain = FlyBrain(config)
    brain.calibrate(receptors)
    kenyon = brain.encode(receptors)
    rng = np.random.default_rng(0)
    first = brain.learn(kenyon, target, rng=rng)
    for _ in range(30):
        last = brain.learn(kenyon, target, rng=rng)
    assert last < first


def test_the_readout_crosses_one_half_on_an_imbalanced_corpus(config):
    """The bug that made a 0.96 AUC circuit answer no to everything."""
    rng = np.random.default_rng(2)
    valence = np.concatenate([rng.normal(0.4, 0.1, 100), rng.normal(-0.4, 0.1, 900)])
    target = np.concatenate([np.ones(100), -np.ones(900)])
    brain = FlyBrain(config)
    brain.fit_readout(valence, target)
    confidence = brain.confidence(valence)
    assert float((confidence[target > 0] >= 0.5).mean()) > 0.9


def test_confidence_is_monotone_in_valence(config):
    brain = FlyBrain(config)
    grid = np.linspace(-1, 1, 50)
    assert np.all(np.diff(brain.confidence(grid)) > 0)


def test_a_saved_fly_is_the_same_fly(config, separable, tmp_path):
    receptors, target = separable
    brain = FlyBrain(config)
    brain.calibrate(receptors)
    kenyon = brain.encode(receptors)
    brain.learn(kenyon, target, rng=np.random.default_rng(0))
    brain.fit_readout(brain.valence(kenyon), target)
    brain.metadata = {"target": "a test tone"}

    path = brain.save(tmp_path / "fly.npz")
    reloaded = FlyBrain.load(path)

    assert reloaded.metadata == brain.metadata
    assert np.array_equal(reloaded.kenyon.claws, brain.kenyon.claws)
    assert np.allclose(reloaded.confidence(reloaded.valence(reloaded.encode(receptors))),
                       brain.confidence(brain.valence(kenyon)))


def test_a_response_covers_every_percept(config, tone):
    brain = FlyBrain(config)
    receptors, t = brain.ear.percepts(tone(6.0))
    brain.calibrate(receptors)
    response = brain.respond(receptors, t)

    assert len(response) == len(t)
    assert response.kenyon.shape == (len(t), config.n_active_kenyon)
    assert response.ear.shape == (len(t), config.channels_per_subframe)
    assert response.confidence.min() >= 0.0 and response.confidence.max() <= 1.0
    assert response.dopamine.min() >= 0.0
