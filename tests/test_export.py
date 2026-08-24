"""Export tests: raw rows helpers and detections.csv roundtrip."""

import numpy as np

from nanotrack.config import PipelineConfig
from nanotrack.export import detections_to_rows, read_detections_rows, track_to_rows, write_csv
from nanotrack.pipeline import run
from nanotrack.synth import generate


def test_detections_rows_and_roundtrip(tmp_path):
    """Raw detection rows contain all fields and reload to the same blob positions."""
    cfg = PipelineConfig(image_size=128, n_frames=10, seed=0)
    frames, _ = generate(cfg)
    result = run(frames, cfg, raw=True)
    rows = detections_to_rows(result["detections"])
    assert rows
    cols = {"frame", "blob_id", "x_px", "y_px", "angle_deg", "angle_rad",
            "length_px", "width_px", "area", "eccentricity"}
    assert cols <= set(rows[0])

    path = tmp_path / "detections.csv"
    write_csv(path, rows)
    loaded = read_detections_rows(path)
    assert len(loaded) == len(result["detections"])
    assert abs(loaded[0][0]["x"] - result["detections"][0][0]["x"]) < 1e-9


def test_track_rows_contain_rad_and_um():
    """Track rows expose angle in deg+rad and positions in px+um."""
    cfg = PipelineConfig(image_size=128, n_frames=10, seed=0)
    frames, _ = generate(cfg)
    result = run(frames, cfg, raw=True)
    rows = track_to_rows(result["track"], cfg)
    assert len(rows) == result["track"]["n_frames"]
    cols = {"track_id", "frame", "x_px", "y_px", "x_um", "y_um", "angle_deg",
            "angle_rad", "length_px", "eccentricity", "missing", "interpolated"}
    assert cols <= set(rows[0])
    present = next(r for r in rows if r["angle_deg"] is not None)
    assert abs(present["angle_rad"] - np.radians(present["angle_deg"])) < 1e-12
    assert abs(present["x_um"] - present["x_px"] * cfg.pixels_per_micron) < 1e-12
