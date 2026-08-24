"""Real-video loaders: TIFF stacks (tifffile) and ND2 (optional ``nd2``).

Both loaders return ``(frames, meta)`` where ``frames`` is a uint8 array of shape
``(n_frames, height, width)`` (docs/implementation-plan.md §5).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np


def _as_uint8_stack(data: np.ndarray) -> np.ndarray:
    """Normalize any numeric array to a uint8 [T, H, W] stack."""
    arr = np.asarray(data)
    if arr.ndim == 2:
        arr = arr[np.newaxis, ...]
    if arr.ndim != 3:
        raise ValueError(f"expected a 2D frame or 3D stack, got shape {arr.shape}")
    if arr.dtype != np.uint8:
        arr = np.clip(np.round(arr.astype(np.float64)), 0, 255).astype(np.uint8)
    return arr


def load_video(path: str | Path) -> tuple[np.ndarray, dict[str, Any]]:
    """Load a TIFF stack or ND2 movie; returns ``(frames, meta)``."""
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix in (".tif", ".tiff"):
        import tifffile

        data = tifffile.imread(path)
        frames = _as_uint8_stack(data)
        meta = {"format": "tiff", "path": str(path), "n_frames": int(frames.shape[0]),
                "height": int(frames.shape[1]), "width": int(frames.shape[2])}
        return frames, meta
    if suffix == ".nd2":
        try:
            import nd2
        except ImportError as exc:  # pragma: no cover - exercised via monkeypatch
            raise ImportError(
                "ND2 support requires the optional 'nd2' package; run `pip install nd2`"
            ) from exc
        with nd2.ND2File(path) as reader:
            data = reader.asarray()
            frames = _as_uint8_stack(data)
            meta = {"format": "nd2", "path": str(path), "n_frames": int(frames.shape[0]),
                    "height": int(frames.shape[1]), "width": int(frames.shape[2])}
        return frames, meta
    raise ValueError(f"unsupported video format {suffix!r}; expected .tif/.tiff or .nd2")


def save_video(path: str | Path, frames: np.ndarray) -> None:
    """Write a [T, H, W] stack as a TIFF (used for roundtrip tests / exports)."""
    import tifffile

    arr = _as_uint8_stack(frames)
    tifffile.imwrite(path, arr)

