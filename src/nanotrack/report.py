"""Standalone Plotly HTML tracking-QC report (ZHA-105)."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from .config import PipelineConfig
from .features import msad_curve, msd_curve, msd_parallel_perpendicular


def _series(track: dict) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    frames = track.get("frames", [])
    xs = np.array([f.get("x_px") for f in frames], dtype=float)
    ys = np.array([f.get("y_px") for f in frames], dtype=float)
    angles = np.array([f.get("angle") for f in frames], dtype=float)
    missing = np.array([bool(f.get("missing", False)) for f in frames])
    interp = np.array([bool(f.get("interpolated", False)) for f in frames])
    return xs, ys, angles, missing, interp


def _panel_max_lag(cfg: PipelineConfig, n: int) -> int:
    """Max lag used by the report MSD/MSAD/par-perp panels.

    Honors an explicit config ``max_lag`` (e.g. a few thousand frames, to reveal
    the Fakhri 2010 Fig. 3B regimes: anisotropic -> perp super-linear ->
    isotropic convergence) but never exceeds ``n // 2``, where the internal
    average would have fewer than two displacement samples. Without an explicit
    value it falls back to the historical 50-frame cap.
    """
    if n < 2:
        return 1
    if cfg.max_lag is None:
        return min(50, max(1, n // 2))
    return max(1, min(int(cfg.max_lag), n // 2))


def build_tracking_report_figure(
    result: dict, cfg: PipelineConfig, frames: np.ndarray | None = None
) -> go.Figure:
    """Build the 3x2 QC figure (trajectory, x/y, angle, MSD + rod-frame
    parallel/perpendicular MSD, MSAD, summary)."""
    track = result.get("track", {})
    xs, ys, angles, missing, interp = _series(track)
    present = ~missing
    fr = np.arange(len(xs), dtype=float)
    # Track angles are stored in degrees; plot them as-is with a truthful axis label.

    fig = make_subplots(
        rows=3,
        cols=2,
        subplot_titles=(
            "Trajectory (px)",
            "x / y vs frame",
            "Angle (deg) vs frame",
            "MSD vs lag (log10)",
            "MSAD vs lag (log10)",
            "Summary",
        ),
    )

    # 1. Trajectory (optionally overlaid on the first frame image).
    if frames is not None and frames.shape[0] > 0:
        # Render the grayscale frame as an explicit RGB image so it is visible and
        # pixel-aligned (x/y in pixel coordinates, row 0 at the top).
        gray = frames[0]
        rgb = np.stack([gray, gray, gray], axis=-1)
        fig.add_trace(
            go.Image(z=rgb, x0=0, y0=0, dx=1, dy=1, hovertemplate="x=%{x}<br>y=%{y}<extra></extra>"),
            row=1,
            col=1,
        )
    fig.add_trace(
        go.Scatter(
            x=xs[present],
            y=ys[present],
            mode="markers+lines",
            name="track",
            line={"width": 2},
        ),
        row=1,
        col=1,
    )
    if np.any(interp):
        fig.add_trace(
            go.Scatter(
                x=xs[interp],
                y=ys[interp],
                mode="markers",
                name="interpolated",
                marker={"color": "orange"},
            ),
            row=1,
            col=1,
        )

    # 2. Position vs frame.
    fig.add_trace(go.Scatter(x=fr[present], y=xs[present], name="x_px"), row=1, col=2)
    fig.add_trace(go.Scatter(x=fr[present], y=ys[present], name="y_px"), row=1, col=2)

    # 3. Unwrapped orientation vs frame.
    fig.add_trace(
        go.Scatter(x=fr[present], y=angles[present], name="angle_deg"), row=2, col=1
    )
    if np.any(interp):
        # Interpolated (gap-filled) angles are bridging estimates; mark them clearly.
        fig.add_trace(
            go.Scatter(
                x=fr[interp],
                y=angles[interp],
                mode="markers",
                name="interpolated angle",
                marker={"color": "orange", "symbol": "x"},
            ),
            row=2,
            col=1,
        )

    # 4. MSD + parallel/perpendicular MSD, log-spaced lags, log-log (base 10)
    # axes. The parallel/perpendicular components follow the author's MATLAB
    # method (mfile092019): each lag-tau displacement is rotated into the rod
    # frame by the interval-averaged orientation, so the two components
    # converge at long times once the orientation memory is lost.
    if present.sum() >= 3:
        lags, msd = msd_curve(
            xs[present],
            ys[present],
            max_lag=_panel_max_lag(cfg, int(present.sum())),
            n_lags=cfg.msd_n_lags,
        )
        if len(lags) > 1:
            fig.add_trace(
                go.Scatter(
                    x=lags,
                    y=msd,
                    mode="markers+lines",
                    name="MSD",
                    line={"color": "#1f77b4", "width": 3},
                    marker={"size": 7},
                ),
                row=2,
                col=2,
            )
        lags_p, msd_par, msd_perp = msd_parallel_perpendicular(
            xs[present],
            ys[present],
            angles[present],
            max_lag=_panel_max_lag(cfg, int(present.sum())),
            n_lags=cfg.msd_n_lags,
        )
        if len(lags_p) > 1:
            fig.add_trace(
                go.Scatter(
                    x=lags_p,
                    y=msd_par,
                    mode="markers+lines",
                    name="MSD parallel",
                    line={"color": "#ff7f0e", "width": 2, "dash": "dash"},
                    marker={"size": 6},
                ),
                row=2,
                col=2,
            )
            fig.add_trace(
                go.Scatter(
                    x=lags_p,
                    y=msd_perp,
                    mode="markers+lines",
                    name="MSD perpendicular",
                    line={"color": "#2ca02c", "width": 2, "dash": "dot"},
                    marker={"size": 6},
                ),
                row=2,
                col=2,
            )

    # 5. MSAD (mean squared angular displacement) with log-spaced lags, log-log axes.
    if present.sum() >= 3:
        ang_present = angles[present]
        lags_a, msad = msad_curve(
            ang_present, max_lag=_panel_max_lag(cfg, int(present.sum())), n_lags=cfg.msd_n_lags
        )
        if len(lags_a) > 1:
            fig.add_trace(
                go.Scatter(x=lags_a, y=msad, mode="markers+lines", name="MSAD"),
                row=3,
                col=1,
            )

    # 6. Summary panel. The figure uses a fixed width/margins so the Summary
    # cell's top-left corner can be computed in paper coordinates; a
    # paper-referenced annotation always renders in the right cell across
    # browsers (domain-referenced annotations on hidden axes do not).
    s = result.get("summary", {}) or {}
    q = result.get("quality", {}) or {}

    def _fmt(value, fmt):
        return fmt % value if value is not None else "n/a"

    # Compact 9-line summary so it fits inside the Summary cell (12 lines at
    # font 11 overflowed the cell height).
    summary_text = (
        f"tracks: {result.get('n_tracks', 'n/a')} | "
        f"pass_rate: {q.get('pass_rate', 'n/a')}<br>"
        f"length_mean: {_fmt(s.get('length_mean'), '%.2f px')} | "
        f"length_std: {_fmt(s.get('length_std'), '%.2f px')}<br>"
        f"angle_std: {_fmt(s.get('angle_std'), '%.2f deg')} | "
        f"eccentricity_mean: {_fmt(s.get('eccentricity_mean'), '%.3f')}<br>"
        f"Dt: {_fmt(s.get('diffusion_coefficient_px2_per_s'), '%.3f px²/s')}<br>"
        f"Dr: {_fmt(s.get('rotational_diffusion_coefficient_rad2_per_s'), '%.5f rad²/s')}<br>"
        f"MSD fit R²: {_fmt(s.get('msd_fit_r2'), '%.3f')}<br>"
        f"D_parallel: {_fmt(s.get('diffusion_coefficient_parallel_px2_per_s'), '%.3f px²/s')}<br>"
        f"D_perpendicular: {_fmt(s.get('diffusion_coefficient_perpendicular_px2_per_s'), '%.3f px²/s')}<br>"
        f"anisotropy D_par/D_perp: {_fmt(s.get('diffusion_anisotropy_ratio'), '%.2f')}"
    )

    # Fixed geometry so the paper-coordinate anchor is deterministic.
    FIG_W, FIG_H = 1200.0, 1100.0
    MARGIN = {"l": 80, "r": 80, "t": 100, "b": 80}
    plot_w = FIG_W - MARGIN["l"] - MARGIN["r"]
    x6_domain = fig.layout.xaxis6.domain
    summary_x = (MARGIN["l"] + x6_domain[0] * plot_w) / FIG_W
    # make_subplots places the "Summary" subplot title with its bottom anchor at
    # paper y=0.2222 (the top of the cell). Anchor the text just below it so the
    # content never renders above/over the title.
    summary_y = 0.2222 - 0.025
    fig.add_annotation(
        xref="paper",
        yref="paper",
        x=summary_x,
        y=summary_y,
        text=summary_text,
        showarrow=False,
        align="left",
        xanchor="left",
        yanchor="top",
        font={"size": 10},
    )

    quality = result.get("quality", {})
    title = (
        f"nanotrack tracking QC — frames={len(xs)} tracks={result.get('n_tracks')} "
        f"pass_rate={quality.get('pass_rate')}"
    )
    fig.update_layout(
        title=title,
        width=FIG_W,
        height=FIG_H,
        margin=MARGIN,
        showlegend=True,
    )
    fig.update_xaxes(title_text="x (px)", row=1, col=1)
    fig.update_yaxes(title_text="y (px)", row=1, col=1, scaleanchor="x")
    fig.update_xaxes(title_text="frame", row=1, col=2)
    fig.update_yaxes(title_text="px", row=1, col=2)
    fig.update_xaxes(title_text="frame", row=2, col=1)
    fig.update_yaxes(title_text="angle (deg)", row=2, col=1)
    fig.update_xaxes(title_text="lag (frames)", row=2, col=2, type="log")
    fig.update_yaxes(title_text="MSD (px^2)", row=2, col=2, type="log")
    fig.update_xaxes(title_text="lag (frames)", row=3, col=1, type="log")
    fig.update_yaxes(title_text="MSAD (rad^2)", row=3, col=1, type="log")
    fig.update_xaxes(visible=False, row=3, col=2)
    fig.update_yaxes(visible=False, row=3, col=2)
    return fig


def build_tracking_report(
    result: dict, cfg: PipelineConfig, frames: np.ndarray | None = None
) -> str:
    """Build a self-contained HTML page: trajectory, x/y, angle, MSD/MSAD, rod-frame MSD."""
    fig = build_tracking_report_figure(result, cfg, frames)
    return fig.to_html(full_html=True, include_plotlyjs=True)


def write_tracking_report(
    result: dict, cfg: PipelineConfig, path: str | Path, frames: np.ndarray | None = None
) -> Path:
    """Build and write the report to ``path``."""
    path = Path(path)
    path.write_text(build_tracking_report(result, cfg, frames), encoding="utf-8")
    return path
