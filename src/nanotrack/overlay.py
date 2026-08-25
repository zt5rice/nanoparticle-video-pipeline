"""Overlay tracking results on the input video (movie / GIF / still image).

Mirrors the MATLAB ``bdmovieSWNT`` movie maker: the tracked trajectory and
orientation are drawn onto each frame, then exported as mp4/avi, gif, or a still
image of the last frame.
"""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from .config import PipelineConfig


def _to_bgr(frame: np.ndarray) -> np.ndarray:
    """Convert a grayscale or color frame to a BGR color image (cv2 convention)."""
    if frame.ndim == 2:
        return cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
    return np.ascontiguousarray(frame)


def _frame_map(track: dict) -> dict[int, dict]:
    """Map frame index -> present tracking entry (non-missing detections)."""
    out: dict[int, dict] = {}
    for f in track.get("frames", []):
        if f.get("x_px") is not None and not f.get("missing"):
            out[int(f["frame"])] = f
    return out


def overlay_tracks(
    frames: np.ndarray,
    track: dict,
    out_path: str | Path,
    cfg: PipelineConfig | None = None,
    format: str | None = None,
    *,
    draw_orientation: bool = True,
    draw_trail: bool = True,
    trail_color=(0, 255, 0),
    marker_color=(0, 0, 255),
    interp_color=(0, 255, 255),
    orientation_color=(255, 0, 0),
) -> Path:
    """Draw the tracked trajectory onto every frame and export the result.

    Supported formats (inferred from ``out_path`` suffix unless ``format`` is given):
    mp4 / avi (cv2.VideoWriter), gif (imageio), png / jpg (still of the last frame).
    """
    out_path = Path(out_path)
    if format is None:
        format = out_path.suffix.lower().lstrip(".")
    fps = float(cfg.fps) if cfg else 16.75
    entries = _frame_map(track)
    trail: list[tuple[float, float]] = []

    rendered: list[np.ndarray] = []
    for t in range(frames.shape[0]):
        img = _to_bgr(frames[t])
        entry = entries.get(t)
        if entry is not None:
            x = float(entry["x_px"])
            y = float(entry["y_px"])
            if draw_trail:
                trail.append((x, y))
                if len(trail) > 1:
                    pts = np.asarray(trail, dtype=np.int32).reshape(-1, 1, 2)
                    cv2.polylines(img, [pts], isClosed=False, color=trail_color, thickness=1)
            color = interp_color if entry.get("interpolated") else marker_color
            cv2.circle(img, (round(float(x)), round(float(y))), 3, color, thickness=-1)
            if draw_orientation and entry.get("angle") is not None:
                # Orientation is mod 180 deg; draw a half-length line along it.
                ang = np.radians(float(entry["angle"]) % 180.0)
                length = float(entry.get("length", 20.0)) * 0.5
                x2 = round(float(x + length * np.cos(ang)))
                y2 = round(float(y + length * np.sin(ang)))
                cv2.line(img, (round(float(x)), round(float(y))), (x2, y2), orientation_color, 1)
        rendered.append(img)

    if format in ("mp4", "avi"):
        h, w = rendered[0].shape[:2]
        fourcc = (
            cv2.VideoWriter_fourcc(*"mp4v")
            if format == "mp4"
            else cv2.VideoWriter_fourcc(*"MJPG")
        )
        writer = cv2.VideoWriter(str(out_path), fourcc, fps, (w, h))
        for img in rendered:
            writer.write(img)
        writer.release()
    elif format == "gif":
        import imageio

        rgb = [cv2.cvtColor(img, cv2.COLOR_BGR2RGB) for img in rendered]
        imageio.mimsave(out_path, rgb, duration=1000.0 / fps)
    elif format in ("png", "jpg", "jpeg"):
        cv2.imwrite(str(out_path), rendered[-1])
    else:
        raise ValueError(
            f"unsupported overlay format {format!r}; expected mp4, avi, gif, png or jpg"
        )
    return out_path
