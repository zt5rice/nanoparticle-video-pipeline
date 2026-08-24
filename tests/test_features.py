"""Feature tests: MSD/MSAD curves, Dt/Dr diffusion coefficients, log-spaced vs
exhaustive lags, and the per-track summary."""

import numpy as np

from nanotrack.config import PipelineConfig
from nanotrack.features import (
    diffusion_coefficient,
    msad_curve,
    msad_curve_full,
    msd_curve,
    msd_curve_full,
    rotational_diffusion_coefficient,
    summarize,
)


def test_msd_linear_random_walk():
    """2D random walk (per-axis step variance 1): MSD(lag) ~= 2*lag -> slope ~= 2."""
    rng = np.random.default_rng(0)
    steps = rng.normal(0.0, 1.0, size=(200, 2))
    pos = np.cumsum(steps, axis=0)
    lags, msd = msd_curve(pos[:, 0], pos[:, 1], 50)
    slope = np.polyfit(lags[:10], msd[:10], 1)[0]
    assert abs(slope - 2.0) < 0.3


def test_diffusion_coefficient_matches_theory():
    """Linear MSD = 2*lag with dt=1 gives Dt = slope/4 = 0.5 px^2/s, R2 ~ 1."""
    lags = np.arange(1, 21, dtype=float)
    msd = 2.0 * lags
    dt, r2 = diffusion_coefficient(lags, msd, dt=1.0, fit_frac=0.5)
    assert abs(dt - 0.5) < 1e-9
    assert r2 > 0.99


def test_msad_wrap():
    """Angular deltas are wrapped to [-180,180): 10 and 20 deg -> 100, 400 deg^2."""
    angles = np.array([0.0, 10.0, 20.0])
    _, msad = msad_curve(angles, 2)
    np.testing.assert_allclose(msad, [100.0, 400.0])


def test_quick_matches_full_at_shared_lags():
    """Log-spaced quick MSD must equal the exhaustive MSD at every shared lag."""
    rng = np.random.default_rng(1)
    pos = np.cumsum(rng.normal(0.0, 1.0, size=(500, 2)), axis=0)
    lags_full, msd_full = msd_curve_full(pos[:, 0], pos[:, 1], max_lag=100)
    lags_q, msd_q = msd_curve(pos[:, 0], pos[:, 1], max_lag=100, n_lags=40)
    idx = np.searchsorted(lags_full, lags_q)
    np.testing.assert_allclose(msd_q, msd_full[idx], rtol=1e-12)


def test_log_lags_ends_and_monotonic():
    """Log-spaced lags: <=40 unique points, start at 1, end at max_lag, increasing."""
    rng = np.random.default_rng(2)
    pos = np.cumsum(rng.normal(0.0, 1.0, size=(1000, 2)), axis=0)
    lags, _ = msd_curve(pos[:, 0], pos[:, 1], max_lag=500, n_lags=40)
    assert len(lags) <= 40
    assert lags[0] == 1
    assert lags[-1] == 500
    assert np.all(np.diff(lags) > 0)


def test_msad_quick_matches_full():
    """Log-spaced quick MSAD must equal the exhaustive MSAD at shared lags."""
    rng = np.random.default_rng(3)
    angles = np.cumsum(rng.normal(0.0, 3.0, size=300))
    lags_full, msad_full = msad_curve_full(angles, max_lag=100)
    lags_q, msad_q = msad_curve(angles, max_lag=100, n_lags=40)
    idx = np.searchsorted(lags_full, lags_q)
    np.testing.assert_allclose(msad_q, msad_full[idx], rtol=1e-12)


def test_rotational_diffusion():
    """Linear MSAD = 2*lag (deg^2/frame) with dt=1 -> Dr = 1 deg^2/s = (pi/180)^2 rad^2/s."""
    lags = np.arange(1, 11, dtype=float)
    msad = 2.0 * lags  # deg^2 per frame
    dr, r2 = rotational_diffusion_coefficient(lags, msad, dt=1.0, fit_frac=0.5)
    assert abs(dr - (np.pi / 180.0) ** 2) < 1e-12
    assert r2 > 0.99


def test_summarize_empty_track():
    """A track with no detections returns None diffusion coefficients (no crash)."""
    cfg = PipelineConfig(n_frames=10, seed=0)
    track = {"frames": [{"frame": i, "missing": True} for i in range(10)]}
    s = summarize(track, cfg)
    assert s["diffusion_coefficient_px2_per_s"] is None
