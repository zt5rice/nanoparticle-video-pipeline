"""Tracking QC report tests."""

import numpy as np

from nanotrack.config import PipelineConfig
from nanotrack.pipeline import run
from nanotrack.report import (
    _panel_max_lag,
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
    # Summary text is anchored in paper coordinates so it renders inside the
    # Summary cell in all browsers (domain-referenced annotations on hidden
    # axes are mispositioned).
    assert '"xref":"paper"' in html

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


def test_panel_max_lag_honors_config_and_caps_at_n_half():
    """The report panels use cfg.max_lag when explicitly set, never exceed n//2,
    and fall back to the historical 50-frame cap when unset."""
    default = PipelineConfig(image_size=64, n_frames=200, seed=0)
    assert default.max_lag == 50
    assert _panel_max_lag(default, 200) == 50

    big = PipelineConfig(image_size=64, n_frames=200, seed=0, max_lag=5000)
    assert big.max_lag == 5000
    assert _panel_max_lag(big, 10_000) == 5000  # explicit value honored
    assert _panel_max_lag(big, 200) == 100  # capped by n//2
    assert _panel_max_lag(big, 2) == 1
