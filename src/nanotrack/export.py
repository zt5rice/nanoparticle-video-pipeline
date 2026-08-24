"""Export raw per-frame data (tracks/detections) for post-processing and resume."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from .config import PipelineConfig


def detections_to_rows(blobs_per_frame: list[list[dict]]) -> list[dict[str, Any]]:
    """Flatten per-frame detections into CSV rows (px + angle in deg and rad)."""
    rows: list[dict[str, Any]] = []
    for frame, blobs in enumerate(blobs_per_frame):
        for b in blobs:
            rows.append(
                {
                    "frame": frame,
                    "blob_id": b["id"],
                    "x_px": b["x"],
                    "y_px": b["y"],
                    "angle_deg": b["angle"],
                    "angle_rad": float(np.radians(b["angle"])),
                    "length_px": b["length"],
                    "width_px": b["width"],
                    "area": b["area"],
                    "eccentricity": b["eccentricity"],
                }
            )
    return rows


def track_to_rows(track: dict, cfg: PipelineConfig) -> list[dict[str, Any]]:
    """Flatten the single track into per-frame CSV rows (px + um, angle in deg and rad)."""
    rows: list[dict[str, Any]] = []
    for f in track["frames"]:
        x = f.get("x_px")
        angle = f.get("angle")
        rows.append(
            {
                "track_id": track["track_id"],
                "frame": f["frame"],
                "x_px": x,
                "y_px": f.get("y_px"),
                "x_um": x * cfg.pixels_per_micron if x is not None else None,
                "y_um": f.get("y_px") * cfg.pixels_per_micron if f.get("y_px") is not None else None,
                "angle_deg": angle,
                "angle_rad": float(np.radians(angle)) if angle is not None else None,
                "length_px": f.get("length"),
                "eccentricity": f.get("eccentricity"),
                "area": f.get("area"),
                "missing": bool(f.get("missing", False)),
                "interpolated": bool(f.get("interpolated", False)),
            }
        )
    return rows


def write_csv(
    path: str | Path, rows: list[dict[str, Any]], columns: list[str] | None = None
) -> None:
    """Write rows to a CSV file (pandas; NaN for empty values)."""
    import pandas as pd

    pd.DataFrame(rows, columns=columns).to_csv(path, index=False)


def read_detections_rows(path: str | Path) -> list[list[dict[str, Any]]]:
    """Reload detections.csv into the ``list[list[blob-dict]]`` shape used by tracking."""
    import pandas as pd

    try:
        df = pd.read_csv(path)
    except pd.errors.EmptyDataError:
        return []
    if df.empty or "frame" not in df.columns:
        return []
    n_frames = int(df["frame"].max()) + 1
    blobs_per_frame: list[list[dict[str, Any]]] = []
    for frame in range(n_frames):
        blobs: list[dict[str, Any]] = []
        for _, r in df[df["frame"] == frame].iterrows():
            blobs.append(
                {
                    "id": int(r["blob_id"]),
                    "x": float(r["x_px"]),
                    "y": float(r["y_px"]),
                    "angle": float(r["angle_deg"]),
                    "length": float(r["length_px"]),
                    "width": float(r["width_px"]),
                    "area": float(r["area"]),
                    "eccentricity": float(r["eccentricity"]),
                }
            )
        blobs_per_frame.append(blobs)
    return blobs_per_frame
