"""Preprocessing tests: numpy backend (MATLAB bpassSWNT threshold port) behavior."""

import numpy as np

from nanotrack.config import PipelineConfig
from nanotrack.preprocessing import matlab_threshold, preprocess
from nanotrack.synth import generate


def test_numpy_backend_returns_bool_mask():
    """Numpy backend returns a non-empty boolean mask matching the frame shape."""
    cfg = PipelineConfig(image_size=128, n_frames=5, seed=0)
    frames, _ = generate(cfg)
    mask = preprocess(frames[0], "numpy", cfg)
    assert mask.dtype == bool
    assert mask.shape == (128, 128)
    assert mask.sum() > 0


def test_threshold_capped_at_0_90():
    """The MATLAB threshold is capped at 0.90 even for a bright flat image."""
    img = np.full((64, 64), 200.0, dtype=np.uint8)
    assert matlab_threshold(img, 3.0) <= 0.90


def test_unsupported_backend_raises():
    """Phase 1 ships only the numpy backend; opencv must raise NotImplementedError."""
    cfg = PipelineConfig(image_size=64, n_frames=2, seed=0)
    frames, _ = generate(cfg)
    try:
        preprocess(frames[0], "opencv", cfg)
    except NotImplementedError:
        return
    raise AssertionError("expected NotImplementedError for opencv in Phase 1")
