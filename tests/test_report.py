"""Tracking QC report tests."""

import numpy as np

from nanotrack.config import PipelineConfig
from nanotrack.pipeline import run
from nanotrack.report import (
    build_tracking_report,
    build_tracking_report_figure,
    write_tracking_report,
)
from nanotrack.synth import generate


def test_report_html_contains_sections(tmp_path):
    cfg = PipelineConfig(image_size=128, n_frames=20, seed=0, min_track_len=5)
    frames, _ = generate(cfg)
    result = run(frames, cfg, raw=True)

    html = build_tracking_report(result, cfg, frames)
    for marker in ("tracking QC", "angle", "MSD", "plotly"):
        assert marker in html
    for marker in (
        "MSD parallel",
        "MSD perpendicular",
        "D_parallel",
        "D_perpendicular",
        "anisotropy",
    ):
        assert marker in html
    # Frame overlay is rendered as a plotly image trace.
    assert '"type":"image"' in html
    # Axis labels are present on all four panels.
    for label in (
        "x (px)", "y (px)", "frame", "angle (deg)", "lag (frames)",
        "MSD (px^2)", "MSAD (rad^2)",
    ):
        assert label in html
    # Log-log (base 10) axes are enabled for both MSD and MSAD panels
    # (x + y for each -> at least 4 log axes).
    assert html.count('"type":"log"') >= 4

    path = write_tracking_report(result, cfg, tmp_path / "tracking_report.html", frames)
    assert path.exists()
    assert path.stat().st_size > 1000


def test_report_angle_plotted_in_degrees():
    """The angle trace must be in degrees (synthetic fluctuation is < 40 deg)."""
    cfg = PipelineConfig(image_size=128, n_frames=30, seed=0, min_track_len=5)
    frames, _ = generate(cfg)
    result = run(frames, cfg, raw=True)
    fig = build_tracking_report_figure(result, cfg, frames)
    angle_trace = next(t for t in fig.data if t.name == "angle_deg")
    y = np.asarray(angle_trace.y, dtype=float)
    assert np.nanmax(np.abs(y)) < 40.0


def test_report_has_parallel_perpendicular_traces():
    """The QC figure contains the rod-frame MSD parallel/perpendicular traces."""
    cfg = PipelineConfig(image_size=128, n_frames=40, seed=0, min_track_len=5)
    frames, _ = generate(cfg)
    result = run(frames, cfg, raw=True)
    fig = build_tracking_report_figure(result, cfg, frames)
    names = {t.name for t in fig.data}
    assert "MSD parallel" in names
    assert "MSD perpendicular" in names
