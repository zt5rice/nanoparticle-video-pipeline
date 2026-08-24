"""Synthetic data tests: video shape/dtype, ground-truth schema, reproducibility."""

import numpy as np

from nanotrack.config import PipelineConfig
from nanotrack.synth import generate


def _cfg(**kw):
    return PipelineConfig(image_size=128, n_frames=10, seed=0, **kw)


def test_shape_and_dtype():
    """Frames are uint8 with shape (n_frames, image_size, image_size) in [0, 255]."""
    frames, _ = generate(_cfg())
    assert frames.shape == (10, 128, 128)
    assert frames.dtype == np.uint8
    assert frames.min() >= 0 and frames.max() <= 255


def test_ground_truth_schema():
    """Ground truth has n_molecules=1 and one per-frame dict with all keys."""
    _, gt = generate(_cfg())
    assert gt["n_molecules"] == 1
    assert len(gt["particles"]) == 10
    keys = {"id", "x", "y", "angle", "length", "width", "area", "intensity"}
    for p in gt["particles"]:
        assert keys <= set(p)
        assert p["id"] == 1


def test_deterministic_with_seed():
    """The same seed must reproduce identical frames."""
    f1, _ = generate(_cfg())
    f2, _ = generate(_cfg())
    np.testing.assert_array_equal(f1, f2)
