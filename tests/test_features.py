import numpy as np

from nanotrack.config import PipelineConfig
from nanotrack.features import (
    diffusion_coefficient,
    msad_curve,
    msd_curve,
    rotational_diffusion_coefficient,
    summarize,
)


def test_msd_linear_random_walk():
    rng = np.random.default_rng(0)
    steps = rng.normal(0.0, 1.0, size=(200, 2))
    pos = np.cumsum(steps, axis=0)
    lags, msd = msd_curve(pos[:, 0], pos[:, 1], 50)
    # 2D random walk with per-axis step variance 1: MSD(lag) ~= 2*lag
    slope = np.polyfit(lags[:10], msd[:10], 1)[0]
    assert abs(slope - 2.0) < 0.3


def test_diffusion_coefficient_matches_theory():
    lags = np.arange(1, 21, dtype=float)
    msd = 2.0 * lags
    dt, r2 = diffusion_coefficient(lags, msd, dt=1.0, fit_frac=0.5)
    assert abs(dt - 0.5) < 1e-9
    assert r2 > 0.99


def test_msad_wrap():
    angles = np.array([0.0, 10.0, 20.0])
    _, msad = msad_curve(angles, 2)
    np.testing.assert_allclose(msad, [100.0, 400.0])


def test_rotational_diffusion():
    lags = np.arange(1, 11, dtype=float)
    msad = 2.0 * lags  # deg^2 per frame
    dr, r2 = rotational_diffusion_coefficient(lags, msad, dt=1.0, fit_frac=0.5)
    # slope=2 deg^2/frame -> Dr = slope/2 = 1 deg^2/s -> rad^2/s
    assert abs(dr - (np.pi / 180.0) ** 2) < 1e-12
    assert r2 > 0.99


def test_summarize_empty_track():
    cfg = PipelineConfig(n_frames=10, seed=0)
    track = {"frames": [{"frame": i, "missing": True} for i in range(10)]}
    s = summarize(track, cfg)
    assert s["diffusion_coefficient_px2_per_s"] is None
