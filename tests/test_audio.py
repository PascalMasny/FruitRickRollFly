"""Johnston's organ: shapes, timing, and the one invariance that matters."""

import numpy as np

from brain.audio import JohnstonsOrgan, chroma_filterbank, level, mel_filterbank


def test_percept_shape_matches_the_configuration(config, tone):
    ear = JohnstonsOrgan(config)
    receptors, t = ear.percepts(tone(4.0))
    assert receptors.shape[1] == config.n_receptors
    assert receptors.shape[0] == t.shape[0]
    assert receptors.dtype == np.float32


def test_percepts_are_evenly_spaced_by_the_hop(config, tone):
    ear = JohnstonsOrgan(config)
    _, t = ear.percepts(tone(6.0))
    gaps = np.diff(t)
    assert np.allclose(gaps, config.window_hop_seconds, atol=1e-5)


def test_the_first_percept_ends_after_one_window(config, tone):
    ear = JohnstonsOrgan(config)
    _, t = ear.percepts(tone(4.0))
    # A percept is reported at the moment its last sample was heard, because
    # that is the earliest the fly could have known anything about it.
    assert t[0] == np.float32(config.window_seconds)


def test_levelling_makes_loudness_irrelevant(config, tone):
    ear = JohnstonsOrgan(config)
    loud, _ = ear.percepts(tone(4.0, gain=1.0))
    quiet, _ = ear.percepts(tone(4.0, gain=0.02))
    assert np.allclose(loud, quiet, rtol=1e-3, atol=1e-4)


def test_shorter_than_one_window_still_yields_a_percept(config):
    ear = JohnstonsOrgan(config)
    receptors, t = ear.percepts(np.zeros(1000, dtype=np.float32))
    assert receptors.shape == (1, config.n_receptors)
    assert len(t) == 1


def test_mel_bank_rows_sum_to_one(config):
    bank = mel_filterbank(config)
    assert bank.shape == (config.n_mel, config.n_fft // 2 + 1)
    assert np.allclose(bank.sum(axis=1), 1.0, atol=1e-5)


def test_chroma_bank_covers_every_pitch_class(config):
    bank = chroma_filterbank(config)
    assert bank.shape == (config.n_chroma, config.chroma_n_fft // 2 + 1)
    assert (bank.sum(axis=1) > 0).all()


def test_a_pure_tone_lands_in_its_own_pitch_class(config):
    ear = JohnstonsOrgan(config)
    sample_rate = config.sample_rate
    t = np.arange(int(3.0 * sample_rate)) / sample_rate
    a440 = np.sin(2 * np.pi * 440.0 * t).astype(np.float32)
    receptors, _ = ear.percepts(level(a440, config.target_rms))
    chroma = receptors[len(receptors) // 2, config.n_mel : config.channels_per_subframe]
    # MIDI 69 is A, pitch class 69 % 12 = 9.
    assert int(np.argmax(chroma)) == 9


def test_silence_stays_silent(config):
    ear = JohnstonsOrgan(config)
    receptors, _ = ear.percepts(np.zeros(3 * config.sample_rate, dtype=np.float32))
    assert float(np.abs(receptors).max()) == 0.0
