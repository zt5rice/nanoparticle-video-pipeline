"""Feature tests: MSD/MSAD curves, Dt/Dr diffusion coefficients, log-spaced vs
exhaustive lags, and the per-track summary."""

import numpy as np

from nanotrack.config import PipelineConfig
from nanotrack.features import (
    component_diffusion_coefficient,
    diffusion_coefficient,
    msad_curve,
    msad_curve_full,
    msd_curve,
    msd_curve_full,
    msd_parallel_perpendicular,
    msd_parallel_perpendicular_full,
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


def test_msad_vertical_rod_no_fake_jump():
    """Orientation is mod 180: a vertical rod at +89/-89 differs by ~2 deg, not 178."""
    angles = np.array([89.0, 90.0, -89.0, -88.0])
    _, msad = msad_curve(angles, 2)
    # physical deltas: lag1 = [1,1,1] -> MSAD ~ 1; lag2 = [2,2] -> MSAD ~ 4
    np.testing.assert_allclose(msad, [1.0, 4.0])


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


def test_msd_parallel_perpendicular_pure_parallel():
    """Rod fixed at 0 deg moving only along its long axis: perp MSD ~ 0."""
    xs = np.arange(200, dtype=float)
    ys = np.zeros(200)
    angles = np.zeros(200)
    _, msd_par, msd_perp = msd_parallel_perpendicular(xs, ys, angles, max_lag=50, n_lags=40)
    assert np.all(msd_perp < 1e-9)
    assert msd_par[0] > 0


def test_msd_parallel_perpendicular_pure_perpendicular():
    """Rod fixed at 0 deg moving only along its short axis: par MSD ~ 0."""
    xs = np.zeros(200)
    ys = np.arange(200, dtype=float)
    angles = np.zeros(200)
    _, msd_par, msd_perp = msd_parallel_perpendicular(xs, ys, angles, max_lag=50, n_lags=40)
    assert np.all(msd_par < 1e-9)
    assert msd_perp[0] > 0


def test_msd_par_plus_perp_equals_total_fixed_angle():
    """With a constant orientation the body frame is fixed, so the orthogonal
    decomposition conserves total squared displacement: par + perp == MSD."""
    rng = np.random.default_rng(5)
    n = 500
    pos = np.cumsum(rng.normal(0.0, 1.0, size=(n, 2)), axis=0)
    angles_deg = np.full(n, 37.0)  # fixed, non-axis-aligned orientation
    _, msd_tot = msd_curve(pos[:, 0], pos[:, 1], max_lag=100, n_lags=40)
    _, msd_par, msd_perp = msd_parallel_perpendicular(
        pos[:, 0], pos[:, 1], angles_deg, max_lag=100, n_lags=40
    )
    np.testing.assert_allclose(msd_par + msd_perp, msd_tot, rtol=1e-9)


def test_msd_par_plus_perp_equals_total_lag_one_rotating():
    """For a single step the midpoint rotation is still orthogonal, so the
    decomposition conserves total squared displacement at lag == 1 even when
    the rod is rotating."""
    rng = np.random.default_rng(7)
    n = 300
    pos = np.cumsum(rng.normal(0.0, 1.0, size=(n, 2)), axis=0)
    angles_deg = np.degrees(np.cumsum(rng.normal(0.0, 0.2, size=n)))
    _, msd_tot = msd_curve(pos[:, 0], pos[:, 1], max_lag=1, n_lags=0, log_spaced=False)
    _, msd_par, msd_perp = msd_parallel_perpendicular(
        pos[:, 0], pos[:, 1], angles_deg, max_lag=1, n_lags=0, log_spaced=False
    )
    np.testing.assert_allclose(msd_par + msd_perp, msd_tot, rtol=1e-9)


def test_msd_parallel_perpendicular_quick_matches_full():
    """Log-spaced quick rod-frame MSD equals the exhaustive version at shared lags."""
    rng = np.random.default_rng(6)
    n = 400
    pos = np.cumsum(rng.normal(0.0, 1.0, size=(n, 2)), axis=0)
    angles = np.degrees(np.cumsum(rng.normal(0.0, 0.1, size=n)))
    lags_f, par_f, perp_f = msd_parallel_perpendicular_full(
        pos[:, 0], pos[:, 1], angles, max_lag=100
    )
    lags_q, par_q, perp_q = msd_parallel_perpendicular(
        pos[:, 0], pos[:, 1], angles, max_lag=100, n_lags=40
    )
    idx = np.searchsorted(lags_f, lags_q)
    np.testing.assert_allclose(par_q, par_f[idx], rtol=1e-12)
    np.testing.assert_allclose(perp_q, perp_f[idx], rtol=1e-12)


def test_component_diffusion_coefficient():
    """1D body-frame MSD = 2*lag (dt=1) -> D = slope/2 = 1 px^2/s."""
    lags = np.arange(1, 21, dtype=float)
    msd = 2.0 * lags
    d, r2 = component_diffusion_coefficient(lags, msd, dt=1.0, fit_frac=0.5)
    assert abs(d - 1.0) < 1e-9
    assert r2 > 0.99


def test_summarize_includes_parallel_perpendicular():
    """Summary carries D_parallel, D_perpendicular and the anisotropy ratio."""
    cfg = PipelineConfig(n_frames=60, seed=0, min_track_len=10, max_lag=20)
    rng = np.random.default_rng(8)
    pos = np.cumsum(rng.normal(0.0, 1.0, size=(60, 2)), axis=0)
    angles = np.degrees(np.cumsum(rng.normal(0.0, 0.05, size=60)))
    frames = [
        {
            "frame": i,
            "x_px": float(pos[i, 0]),
            "y_px": float(pos[i, 1]),
            "angle": float(angles[i]),
            "length": 40.0,
            "eccentricity": 0.9,
            "area": 100.0,
            "missing": False,
            "interpolated": False,
        }
        for i in range(60)
    ]
    track = {"track_id": 1, "frames": frames, "present_frames": 60, "valid": True}
    s = summarize(track, cfg)
    assert s["diffusion_coefficient_parallel_px2_per_s"] is not None
    assert s["diffusion_coefficient_perpendicular_px2_per_s"] is not None
    assert s["diffusion_anisotropy_ratio"] is not None


def test_summarize_empty_track():
    """A track with no detections returns None diffusion coefficients (no crash)."""
    cfg = PipelineConfig(n_frames=10, seed=0)
    track = {"frames": [{"frame": i, "missing": True} for i in range(10)]}
    s = summarize(track, cfg)
    assert s["diffusion_coefficient_px2_per_s"] is None
    assert s["diffusion_coefficient_parallel_px2_per_s"] is None
    assert s["diffusion_coefficient_perpendicular_px2_per_s"] is None
    assert s["diffusion_anisotropy_ratio"] is None
