"""Preprocessing backends (docs/implementation-plan.md §5).

- ``numpy`` (reference): faithful port of the MATLAB ``bpassSWNT`` global threshold.
- ``opencv``: same threshold logic + optional Gaussian denoise + morphology open.
- ``skimage``: Otsu threshold + morphology open.
"""

from __future__ import annotations

import numpy as np

from .config import PipelineConfig

# Components at or below this many pixels are treated as speckle noise in the
# skimage backend (removed after Otsu + opening). 80 px << molecule area (~190 px).
_SKIMAGE_MIN_BLOB_AREA = 80


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


def preprocess_opencv(frame: np.ndarray, cfg: PipelineConfig) -> np.ndarray:
    """OpenCV backend: Gaussian denoise -> MATLAB global threshold -> morphology open."""
    import cv2

    img = frame.astype(np.float32)
    # Optional denoise: small Gaussian blur removes pixel noise before thresholding.
    img = cv2.GaussianBlur(img, (3, 3), sigmaX=1.0)
    level = matlab_threshold(img, cfg.threshold_mult)
    _, binary = cv2.threshold(img, level * 255.0, 255.0, cv2.THRESH_BINARY)
    # Morphology open removes small speckle noise while keeping the molecule.
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    opened = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)
    return opened > 0


def preprocess_skimage(frame: np.ndarray, cfg: PipelineConfig) -> np.ndarray:
    """scikit-image backend: smooth-background subtraction -> median -> Otsu -> opening.

    A plain Otsu threshold on dark-field frames splits the background noise instead of
    isolating the molecule, so the background is flattened first (ImageJ-style).
    """
    from skimage import filters, morphology

    img = frame.astype(np.float64)
    # Estimate the smooth background with a large Gaussian and subtract it.
    background = filters.gaussian(img, sigma=25.0)
    flat = np.clip(img - background, 0.0, None)
    # Median denoise, then Otsu on the flattened image.
    median = filters.median(flat, footprint=morphology.disk(2))
    mask = morphology.opening(median > filters.threshold_otsu(median), footprint=morphology.disk(2))
    # Drop remaining speckle components (newer API: remove objects <= max_size).
    return morphology.remove_small_objects(mask, max_size=_SKIMAGE_MIN_BLOB_AREA)


def preprocess(frame: np.ndarray, backend: str, cfg: PipelineConfig) -> np.ndarray:
    """Dispatch to a preprocessing backend and return a boolean mask."""
    if backend == "numpy":
        return preprocess_numpy(frame, cfg)
    if backend == "opencv":
        return preprocess_opencv(frame, cfg)
    if backend == "skimage":
        return preprocess_skimage(frame, cfg)
    raise ValueError(f"unknown backend {backend!r}; expected one of numpy|opencv|skimage")
