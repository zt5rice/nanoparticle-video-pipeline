"""Pipeline integration test: end-to-end result schema on synthetic data."""

import json
from itertools import pairwise

from nanotrack.config import PipelineConfig
from nanotrack.pipeline import run
from nanotrack.synth import generate


def test_pipeline_result_schema():
    """run() returns the documented result keys, n_tracks=1, JSON-serializable output."""
    cfg = PipelineConfig(image_size=128, n_frames=20, seed=0, min_track_len=5)
    frames, gt = generate(cfg)
    result = run(frames, cfg, gt)
    assert result["n_frames"] == 20
    assert result["n_tracks"] == 1
    assert set(result["quality"]) == {"pass_rate", "checks"}
    assert result["summary"]["length_mean"] is not None
    json.dumps(result)


def test_vertical_rod_no_fake_angle_jump():
    """A rod vibrating at vertical orientation must not produce fake angle jumps."""
    cfg = PipelineConfig(
        image_size=128, n_frames=40, seed=0, initial_angle_deg=90.0, min_track_len=10
    )
    frames, _ = generate(cfg)
    result = run(frames, cfg, raw=True)
    assert result["n_tracks"] == 1
    angles = [f["angle"] for f in result["track"]["frames"] if f.get("angle") is not None]
    steps = [abs(b - a) for a, b in pairwise(angles)]
    assert max(steps) < 20.0, f"fake orientation jump: {max(steps):.1f} deg"
    assert result["summary"]["angle_std"] < 20.0
