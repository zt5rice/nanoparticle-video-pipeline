"""Preprocessing tests: all three backends (numpy/opencv/skimage) mask behavior."""

import numpy as np

from nanotrack.config import BACKENDS, PipelineConfig
from nanotrack.detection import detect
from nanotrack.preprocessing import matlab_threshold, preprocess
from nanotrack.synth import generate


def test_all_backends_return_valid_masks():
    """Each backend returns a non-empty boolean mask matching the frame shape."""
    cfg = PipelineConfig(image_size=128, n_frames=5, seed=0)
    frames, _ = generate(cfg)
    for backend in BACKENDS:
        mask = preprocess(frames[0], backend, cfg)
        assert mask.dtype == bool
        assert mask.shape == (128, 128)
        assert mask.sum() > 0


def test_backends_primary_object_consistent():
    """All backends find the same primary molecule (position within tolerance)."""
    cfg = PipelineConfig(image_size=128, n_frames=10, seed=0)
    frames, _ = generate(cfg)
    positions: dict[str, tuple[float, float]] = {}
    for backend in BACKENDS:
        mask = preprocess(frames[0], backend, cfg)
        blobs = detect(mask, cfg)
        assert len(blobs) >= 1
        positions[backend] = (blobs[0]["x"], blobs[0]["y"])
    ref = positions["numpy"]
    for backend, pos in positions.items():
        assert abs(pos[0] - ref[0]) < 8.0, backend
        assert abs(pos[1] - ref[1]) < 8.0, backend


def test_threshold_capped_at_0_90():
    """The MATLAB threshold is capped at 0.90 even for a bright flat image."""
    img = np.full((64, 64), 200.0, dtype=np.uint8)
    assert matlab_threshold(img, 3.0) <= 0.90


def test_unknown_backend_raises():
    """An unknown backend name must raise ValueError."""
    cfg = PipelineConfig(image_size=64, n_frames=2, seed=0)
    frames, _ = generate(cfg)
    try:
        preprocess(frames[0], "nope", cfg)
    except ValueError:
        return
    raise AssertionError("expected ValueError for unknown backend")
