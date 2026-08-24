"""Track features: MSD/MSAD with internal averaging, diffusion coefficients, and
shape-fluctuation statistics (Gittes-style bending angle is Phase 2+; v1 reports
length/angle/eccentricity statistics)."""

from __future__ import annotations

import numpy as np

from .config import PipelineConfig


def _positions(track: dict) -> tuple[np.ndarray, np.ndarray]:
    xs = np.array([f["x_px"] for f in track["frames"] if f.get("x_px") is not None], dtype=float)
    ys = np.array([f["y_px"] for f in track["frames"] if f.get("x_px") is not None], dtype=float)
    return xs, ys


def _angles_deg(track: dict) -> np.ndarray:
    return np.array(
        [f["angle"] for f in track["frames"] if f.get("x_px") is not None], dtype=float
    )


def _wrap_deg(delta: np.ndarray, period: float = 360.0) -> np.ndarray:
    """Wrap angular differences to [-period/2, period/2)."""
    half = period / 2.0
    return (delta + half) % period - half


def _log_spaced_lags(max_lag: int, n_lags: int) -> np.ndarray:
    """Lags evenly distributed in log scale (1 .. max_lag), unique and sorted."""
    if max_lag <= 0 or n_lags <= 0:
        return np.array([], dtype=int)
    lags = np.unique(
        np.round(np.logspace(np.log10(1.0), np.log10(max_lag), int(n_lags))).astype(int)
    )
    return lags[(lags >= 1) & (lags <= max_lag)]


def msd_curve(
    xs: np.ndarray,
    ys: np.ndarray,
    max_lag: int | None = None,
    n_lags: int = 40,
    log_spaced: bool = True,
) -> tuple[np.ndarray, np.ndarray]:
    """Internal-averaging MSD: mean squared displacement over all position pairs.

    ``log_spaced=True`` (default) evaluates ~``n_lags`` lags evenly distributed in
    log scale — O(n_lags * N) and the standard choice for long videos (e.g. 10k frames,
    40 points). ``log_spaced=False`` evaluates every lag 1..max_lag (exhaustive; used by
    ``msd_curve_full`` for tests/correctness).
    """
    n = len(xs)
    if max_lag is None:
        max_lag = n - 1
    max_lag = int(min(max_lag, n - 1))
    if max_lag < 1 or n < 2:
        return np.array([], dtype=float), np.array([], dtype=float)
    lags = _log_spaced_lags(max_lag, n_lags) if log_spaced else np.arange(1, max_lag + 1)
    msd = np.empty(len(lags), dtype=float)
    for k, lag in enumerate(lags):
        dx = xs[lag:] - xs[:-lag]
        dy = ys[lag:] - ys[:-lag]
        msd[k] = float(np.mean(dx * dx + dy * dy))
    return lags.astype(float), msd


def msd_curve_full(
    xs: np.ndarray, ys: np.ndarray, max_lag: int | None = None
) -> tuple[np.ndarray, np.ndarray]:
    """Exhaustive MSD over every lag (test/correctness helper)."""
    return msd_curve(xs, ys, max_lag=max_lag, n_lags=0, log_spaced=False)


def msad_curve(
    angles_deg: np.ndarray,
    max_lag: int | None = None,
    n_lags: int = 40,
    log_spaced: bool = True,
) -> tuple[np.ndarray, np.ndarray]:
    """Internal-averaging MSAD (angular displacement squared, wrapped).

    Same lag-sampling options as :func:`msd_curve`.
    """
    n = len(angles_deg)
    if max_lag is None:
        max_lag = n - 1
    max_lag = int(min(max_lag, n - 1))
    if max_lag < 1 or n < 2:
        return np.array([], dtype=float), np.array([], dtype=float)
    lags = _log_spaced_lags(max_lag, n_lags) if log_spaced else np.arange(1, max_lag + 1)
    msad = np.empty(len(lags), dtype=float)
    for k, lag in enumerate(lags):
        # Orientation is periodic with 180 deg, so wrap to [-90, 90): a rod at +89
        # and -89 differ by only 2 deg, not 178.
        delta = _wrap_deg(angles_deg[lag:] - angles_deg[:-lag], period=180.0)
        msad[k] = float(np.mean(delta * delta))
    return lags.astype(float), msad


def msad_curve_full(
    angles_deg: np.ndarray, max_lag: int | None = None
) -> tuple[np.ndarray, np.ndarray]:
    """Exhaustive MSAD over every lag (test/correctness helper)."""
    return msad_curve(angles_deg, max_lag=max_lag, n_lags=0, log_spaced=False)


def _linear_fit(y: np.ndarray, x: np.ndarray) -> tuple[float, float, float]:
    if len(x) < 2:
        return 0.0, 0.0, 0.0
    A = np.vstack([x, np.ones_like(x)]).T
    slope, intercept = np.linalg.lstsq(A, y, rcond=None)[0]
    resid = y - (slope * x + intercept)
    ss_res = float(np.sum(resid**2))
    ss_tot = float(np.sum((y - np.mean(y)) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0
    return float(slope), float(intercept), float(r2)


def diffusion_coefficient(
    lags: np.ndarray, msd: np.ndarray, dt: float, fit_frac: float = 0.25
) -> tuple[float, float]:
    """Dt (px^2/s) from linear fit slope / 4 over the first ``fit_frac`` lags."""
    if len(lags) < 2 or dt <= 0:
        return 0.0, 0.0
    nfit = max(2, round(len(lags) * fit_frac))
    slope, _, r2 = _linear_fit(msd[:nfit], lags[:nfit])
    return slope / 4.0 / dt, r2


def rotational_diffusion_coefficient(
    lags: np.ndarray, msad: np.ndarray, dt: float, fit_frac: float = 0.25
) -> tuple[float, float]:
    """Dr (rad^2/s) from MSAD slope / 2, converted from deg^2 to rad^2."""
    if len(lags) < 2 or dt <= 0:
        return 0.0, 0.0
    nfit = max(2, round(len(lags) * fit_frac))
    slope, _, r2 = _linear_fit(msad[:nfit], lags[:nfit])
    dr_deg2_per_s = slope / 2.0 / dt
    return dr_deg2_per_s * (np.pi / 180.0) ** 2, r2


def summarize(track: dict, cfg: PipelineConfig) -> dict:
    """Return the per-track summary dict (spec §5)."""
    xs, ys = _positions(track)
    if len(xs) < 2:
        return {
            "track_id": 1,
            "length_mean": None,
            "length_std": None,
            "angle_std": None,
            "eccentricity_mean": None,
            "diffusion_coefficient_px2_per_s": None,
            "rotational_diffusion_coefficient_rad2_per_s": None,
            "msd_fit_r2": None,
        }

    lengths = np.array([f["length"] for f in track["frames"] if f.get("x_px") is not None], dtype=float)
    eccs = np.array([f["eccentricity"] for f in track["frames"] if f.get("x_px") is not None], dtype=float)
    angles = _angles_deg(track)

    lags, msd = msd_curve(xs, ys, cfg.max_lag, n_lags=cfg.msd_n_lags)
    dt_px2, msd_r2 = diffusion_coefficient(lags, msd, cfg.dt, cfg.msd_fit_frac)
    lags_a, msad = msad_curve(angles, cfg.max_lag, n_lags=cfg.msd_n_lags)
    dr_rad2, _msad_r2 = rotational_diffusion_coefficient(lags_a, msad, cfg.dt, cfg.msd_fit_frac)

    return {
        "track_id": 1,
        "length_mean": float(np.mean(lengths)) if len(lengths) else None,
        "length_std": float(np.std(lengths)) if len(lengths) else None,
        "angle_std": float(np.std(angles)) if len(angles) else None,
        "eccentricity_mean": float(np.mean(eccs)) if len(eccs) else None,
        "diffusion_coefficient_px2_per_s": float(dt_px2) if len(lags) >= 2 else None,
        "rotational_diffusion_coefficient_rad2_per_s": float(dr_rad2) if len(lags_a) >= 2 else None,
        "msd_fit_r2": float(msd_r2) if len(lags) >= 2 else None,
    }
