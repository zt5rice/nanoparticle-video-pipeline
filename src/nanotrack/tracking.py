"""Single-object tracking (SPT): nearest blob within max_disp + gap interpolation.

Mirrors the MATLAB ``putting_in_missing_frames6`` semantics: missing frames within
``memory`` are back-filled by linear interpolation between surrounding present frames.
"""

from __future__ import annotations

import numpy as np

from .config import PipelineConfig


def _interpolate_missing(frames: list[dict], memory: int) -> list[dict]:
    """Linearly interpolate x/y/angle/length/eccentricity across missing frames."""
    n = len(frames)
    present_idx = [i for i, f in enumerate(frames) if not f["missing"] and f.get("x_px") is not None]
    if not present_idx:
        return frames
    filled = [dict(f) for f in frames]

    def lerp(a, b, t):
        return a + (b - a) * t

    for i in range(n):
        if filled[i]["missing"] or filled[i].get("x_px") is None:
            # find surrounding present frames
            before = [j for j in present_idx if j < i]
            after = [j for j in present_idx if j > i]
            if before and after:
                j0, j1 = before[-1], after[0]
                span = j1 - j0
                if span - 1 <= memory:
                    t = (i - j0) / span
                    for key in ("x_px", "y_px", "angle", "length", "eccentricity"):
                        v0 = filled[j0].get(key)
                        v1 = filled[j1].get(key)
                        if v0 is not None and v1 is not None:
                            filled[i][key] = lerp(v0, v1, t)
                    filled[i]["interpolated"] = True
                    filled[i]["missing"] = False
    return filled


def _unwrap_orientation(frames: list[dict]) -> list[dict]:
    """Unwrap orientation (mod 180 deg) so vertical rods don't fake-jump at ±90.

    Ellipse orientation is defined in (-90, 90]; unwrapping keeps the series
    continuous (e.g. 89 -> 91 instead of 89 -> -89), which is what angle_std,
    MSAD and tracks.csv should reflect.
    """
    prev: float | None = None
    for f in frames:
        a = f.get("angle")
        if a is None or f.get("missing"):
            continue
        if prev is None:
            prev = float(a)
            continue
        delta = (float(a) - prev + 90.0) % 180.0 - 90.0  # smallest rotation (mod 180)
        f["angle"] = prev + delta
        prev = f["angle"]
    return frames


def track(blobs_per_frame: list[list[dict]], cfg: PipelineConfig) -> dict:
    """Track the single primary object across frames.

    Returns a Track dict per docs/implementation-plan.md §5.
    """
    frames: list[dict] = []
    last: tuple[float, float] | None = None
    present = 0

    for t, blobs in enumerate(blobs_per_frame):
        if not blobs:
            frames.append({"frame": t, "missing": True})
            continue
        primary = blobs[0]  # largest-area blob
        if last is not None:
            dist = float(np.hypot(primary["x"] - last[0], primary["y"] - last[1]))
            if dist > cfg.max_disp:
                frames.append({"frame": t, "missing": True})
                continue
        frames.append(
            {
                "frame": t,
                "x_px": primary["x"],
                "y_px": primary["y"],
                "angle": primary["angle"],
                "length": primary["length"],
                "eccentricity": primary["eccentricity"],
                "area": primary["area"],
                "missing": False,
            }
        )
        last = (primary["x"], primary["y"])
        present += 1

    frames = _unwrap_orientation(frames)
    filled = _interpolate_missing(frames, cfg.memory)
    valid = present >= cfg.min_track_len
    return {
        "track_id": 1,
        "frames": filled,
        "n_frames": int(cfg.n_frames),
        "present_frames": present,
        "valid": bool(valid),
        "x_um": [f.get("x_px") * cfg.pixels_per_micron if f.get("x_px") is not None else None for f in filled],
        "y_um": [f.get("y_px") * cfg.pixels_per_micron if f.get("y_px") is not None else None for f in filled],
    }
