import numpy as np
import pytest

from brain.config import BrainConfig


@pytest.fixture
def config() -> BrainConfig:
    """A small fly, so the tests run in milliseconds rather than seconds."""
    return BrainConfig(n_kenyon=400, kc_sparsity=0.05, n_claws=8)


@pytest.fixture
def tone():
    """A chord plus noise, long enough to make a handful of percepts."""

    def build(seconds: float = 4.0, sample_rate: int = 22_050, seed: int = 0, gain: float = 1.0):
        rng = np.random.default_rng(seed)
        t = np.arange(int(seconds * sample_rate)) / sample_rate
        wave = sum(np.sin(2 * np.pi * f * t) for f in (220.0, 277.2, 330.0))
        wave = wave + 0.15 * rng.standard_normal(t.size)
        return (gain * wave / np.abs(wave).max()).astype(np.float32)

    return build
