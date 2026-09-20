"""Gain control, the calyx, and the synapses dopamine is allowed to touch."""

import numpy as np
import pytest

from brain.layers import AntennalLobe, KenyonCells, MBONCompartment


@pytest.fixture
def receptors(config):
    rng = np.random.default_rng(3)
    return rng.random((256, config.n_receptors), dtype=np.float32) * rng.choice(
        [0.05, 1.0, 20.0], size=(256, 1)
    ).astype(np.float32)


def test_gain_control_bounds_its_output(config, receptors):
    lobe = AntennalLobe(config)
    lobe.calibrate(receptors)
    out = lobe.transform(receptors)
    assert out.min() >= 0.0
    assert out.max() <= config.al_rmax + 1e-6


def test_gain_control_discards_overall_level(config):
    rng = np.random.default_rng(5)
    pattern = rng.random((8, config.n_receptors), dtype=np.float32) + 0.5
    lobe = AntennalLobe(config)
    quiet = lobe.transform(pattern * 4.0)
    loud = lobe.transform(pattern * 40.0)
    # Not identical, because the sigma term keeps an absolute reference, but
    # the ranking of channels inside a pool must survive a tenfold change.
    for lo, hi in config.blocks():
        assert np.array_equal(
            np.argsort(quiet[0, lo:hi]), np.argsort(loud[0, lo:hi])
        )


def test_calibration_gives_every_channel_a_working_point(config, receptors):
    lobe = AntennalLobe(config)
    lobe.calibrate(receptors)
    assert lobe.gains.shape == (config.n_receptors,)
    assert (lobe.gains > 0).all()


def test_exactly_the_sparse_fraction_fires(config, receptors):
    lobe = AntennalLobe(config)
    lobe.calibrate(receptors)
    projection = lobe.transform(receptors)
    kenyon = KenyonCells(config)
    kenyon.calibrate(projection)
    active = kenyon.respond(projection)
    assert active.shape == (len(receptors), config.n_active_kenyon)
    for row in active:
        assert len(set(row.tolist())) == config.n_active_kenyon


def test_the_claw_table_is_the_same_every_time(config):
    assert np.array_equal(KenyonCells(config).claws, KenyonCells(config).claws)


def test_excitability_homeostasis_spreads_the_code_out(config, receptors):
    lobe = AntennalLobe(config)
    lobe.calibrate(receptors)
    projection = lobe.transform(receptors)

    naive = KenyonCells(config)
    tuned = KenyonCells(config)
    tuned.calibrate(projection)

    used = lambda cells: len(np.unique(cells.respond(projection)))  # noqa: E731
    assert used(tuned) > used(naive)


def test_densify_agrees_with_the_sparse_form(config, receptors):
    lobe = AntennalLobe(config)
    lobe.calibrate(receptors)
    projection = lobe.transform(receptors)
    kenyon = KenyonCells(config)
    kenyon.calibrate(projection)
    active = kenyon.respond(projection)

    compartment = MBONCompartment("approach", config)
    compartment.weights = np.linspace(0, 2, config.n_kenyon, dtype=np.float32)
    dense = kenyon.densify(active)
    assert np.allclose(
        compartment.respond(active),
        (dense @ compartment.weights) / config.n_active_kenyon,
        atol=1e-5,
    )


def test_a_resting_compartment_reports_baseline(config):
    compartment = MBONCompartment("approach", config)
    active = np.arange(config.n_active_kenyon)[None, :]
    assert compartment.respond(active) == pytest.approx(config.w_baseline)


def test_dopamine_only_depresses_the_cells_that_fired(config):
    compartment = MBONCompartment("avoidance", config)
    active = np.array([[0, 1, 2, 3, 4]])
    untouched = compartment.weights[10]
    compartment.depress(active, np.array([1.0]))
    assert (compartment.weights[:5] < config.w_baseline).all()
    assert compartment.weights[10] == untouched


def test_depression_accumulates_over_a_batch(config):
    once = MBONCompartment("avoidance", config)
    twice = MBONCompartment("avoidance", config)
    active = np.array([[0, 1, 2]])
    once.depress(active, np.array([1.0]))
    twice.depress(np.repeat(active, 2, axis=0), np.array([1.0, 1.0]))
    assert twice.weights[0] < once.weights[0]


def test_weights_never_leave_their_bounds(config):
    compartment = MBONCompartment("avoidance", config)
    active = np.array([[0, 1, 2]])
    for _ in range(500):
        compartment.depress(active, np.array([10.0]))
    assert compartment.weights.min() >= config.w_min
    assert compartment.weights.max() <= config.w_max


def test_recovery_walks_back_towards_baseline(config):
    compartment = MBONCompartment("avoidance", config)
    compartment.depress(np.array([[0, 1, 2]]), np.array([5.0]))
    depressed = compartment.weights[0]
    compartment.recover(steps=2000)
    assert compartment.weights[0] > depressed
    assert compartment.weights[0] <= config.w_baseline + 1e-6
