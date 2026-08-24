"""Detection tests: connected-component labeling and moment-based ellipse features."""

import numpy as np

from nanotrack.config import PipelineConfig
from nanotrack.detection import detect, label_components
from nanotrack.preprocessing import preprocess
from nanotrack.synth import generate


def test_label_components_counts_blobs():
    """Two disjoint foreground squares must be labeled as two separate components."""
    mask = np.zeros((32, 32), dtype=bool)
    mask[4:8, 4:8] = True
    mask[20:25, 20:25] = True
    labels, n = label_components(mask)
    assert n == 2
    assert labels.max() == 2


def test_detect_finds_primary_object_near_truth():
    """Largest blob from a synthetic frame lands near the ground-truth molecule."""
    cfg = PipelineConfig(image_size=128, n_frames=10, seed=0)
    frames, gt = generate(cfg)
    mask = preprocess(frames[0], "numpy", cfg)
    blobs = detect(mask, cfg)
    assert len(blobs) >= 1
    b = blobs[0]
    truth = gt["particles"][0]
    assert abs(b["x"] - truth["x"]) < 15
    assert abs(b["y"] - truth["y"]) < 15
    assert 0.3 * truth["length"] < b["length"] < 3.0 * truth["length"]


def test_detect_empty_mask():
    """An empty mask must yield no blobs."""
    cfg = PipelineConfig(image_size=64, n_frames=2, seed=0)
    assert detect(np.zeros((64, 64), dtype=bool), cfg) == []
