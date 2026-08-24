"""Pipeline integration test: end-to-end result schema on synthetic data."""

import json

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
