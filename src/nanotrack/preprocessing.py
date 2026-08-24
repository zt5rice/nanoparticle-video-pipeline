"""Preprocessing backends. The numpy backend is a faithful port of the MATLAB
``bpassSWNT`` global threshold (docs/implementation-plan.md §5)."""

from __future__ import annotations

import numpy as np

from .config import PipelineConfig


def matlab_threshold(frame: np.ndarray, threshold_mult: float) -> float:
    """Return the normalized binary threshold of ``bpassSWNT`` (cap 0.90)."""
    img = frame.astype(np.float64)
    # MATLAB: std(std(double(img),1,2)); outer std uses default normalization.
    imgstd = float(np.std(np.std(img, axis=1)))
    imgmean = float(np.mean(img))
    level = (imgstd + threshold_mult * imgmean) / 256.0
    return min(level, 0.90)


def preprocess_numpy(frame: np.ndarray, cfg: PipelineConfig) -> np.ndarray:
    """Global-threshold binarization (bright pixels -> True)."""
    level = matlab_threshold(frame, cfg.threshold_mult)
    return frame > level * 255.0


def preprocess(frame: np.ndarray, backend: str, cfg: PipelineConfig) -> np.ndarray:
    """Dispatch to a preprocessing backend and return a boolean mask."""
    if backend == "numpy":
        return preprocess_numpy(frame, cfg)
    raise NotImplementedError(
        f"backend {backend!r} is planned for Phase 2; only 'numpy' is available in Phase 1"
    )

