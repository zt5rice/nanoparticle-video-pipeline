"""Standalone Plotly HTML tracking-QC report (ZHA-105)."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from .config import PipelineConfig
from .features import msd_curve


def _series(track: dict) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    frames = track.get("frames", [])
    xs = np.array([f.get("x_px") for f in frames], dtype=float)
    ys = np.array([f.get("y_px") for f in frames], dtype=float)
    angles = np.array([f.get("angle") for f in frames], dtype=float)
    missing = np.array([bool(f.get("missing", False)) for f in frames])
    interp = np.array([bool(f.get("interpolated", False)) for f in frames])
    return xs, ys, angles, missing, interp


def build_tracking_report_figure(
    result: dict, cfg: PipelineConfig, frames: np.ndarray | None = None
) -> go.Figure:
    """Build the 2x2 QC figure (trajectory, x/y, angle in rad, MSD)."""
    track = result.get("track", {})
    xs, ys, angles, missing, interp = _series(track)
    present = ~missing
    fr = np.arange(len(xs), dtype=float)
    # Track angles are stored in degrees; plot them as-is with a truthful axis label.

    fig = make_subplots(
        rows=2,
        cols=2,
        subplot_titles=("Trajectory (px)", "x / y vs frame", "Angle (rad) vs frame", "MSD vs lag"),
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

    # 4. MSD with log-spaced lags.
    if present.sum() >= 3:
        lags, msd = msd_curve(
            xs[present], ys[present], max_lag=min(50, int(present.sum()) // 2), n_lags=20
        )
        if len(lags) > 1:
            fig.add_trace(
                go.Scatter(x=lags, y=msd, mode="markers+lines", name="MSD"), row=2, col=2
            )

    quality = result.get("quality", {})
    title = (
        f"nanotrack tracking QC — frames={len(xs)} tracks={result.get('n_tracks')} "
        f"pass_rate={quality.get('pass_rate')}"
    )
    fig.update_layout(title=title, height=800, showlegend=True)
    fig.update_xaxes(title_text="x (px)", row=1, col=1)
    fig.update_yaxes(title_text="y (px)", row=1, col=1, scaleanchor="x")
    fig.update_xaxes(title_text="frame", row=1, col=2)
    fig.update_yaxes(title_text="px", row=1, col=2)
    fig.update_xaxes(title_text="frame", row=2, col=1)
    fig.update_yaxes(title_text="angle (deg)", row=2, col=1)
    fig.update_xaxes(title_text="lag (frames)", row=2, col=2)
    fig.update_yaxes(title_text="MSD (px^2)", row=2, col=2)
    return fig


def build_tracking_report(
    result: dict, cfg: PipelineConfig, frames: np.ndarray | None = None
) -> str:
    """Build a self-contained HTML page: trajectory, x/y, angle, MSD."""
    fig = build_tracking_report_figure(result, cfg, frames)
    return fig.to_html(full_html=True, include_plotlyjs=True)


def write_tracking_report(
    result: dict, cfg: PipelineConfig, path: str | Path, frames: np.ndarray | None = None
) -> Path:
    """Build and write the report to ``path``."""
    path = Path(path)
    path.write_text(build_tracking_report(result, cfg, frames), encoding="utf-8")
    return path
