"""Synthetic fluorescence video of a single rod-like molecule (Brownian motion)."""

from __future__ import annotations

import numpy as np

from .config import PipelineConfig


def _render_ellipse(
    img: np.ndarray,
    cx: float,
    cy: float,
    angle_deg: float,
    major: float,
    minor: float,
    peak: float,
) -> None:
    """Add a soft-edged Gaussian ellipse to ``img`` in place."""
    h, w = img.shape
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float64)
    theta = np.radians(angle_deg)
    cos, sin = np.cos(theta), np.sin(theta)
    dx, dy = xx - cx, yy - cy
    u = dx * cos + dy * sin
    v = -dx * sin + dy * cos
    a = max(major / 2.0, 1.0)
    b = max(minor / 2.0, 1.0)
    r2 = (u / a) ** 2 + (v / b) ** 2
    img += peak * np.exp(-0.5 * r2)


def generate(cfg: PipelineConfig) -> tuple[np.ndarray, dict]:
    """Generate ``(frames, ground_truth)`` with exactly one molecule per video.

    frames: uint8 array of shape ``(n_frames, image_size, image_size)``.
    ground_truth: ``{"n_molecules": 1, "particles": [per-frame dicts]}``.
    """
    rng = np.random.default_rng(cfg.seed)
    h = w = cfg.image_size
    n = cfg.n_frames

    yy, xx = np.mgrid[0:h, 0:w].astype(np.float64)
    grad = (xx + yy) / float(h + w)
    background = 10.0 + cfg.background_strength * grad

    frames = np.zeros((n, h, w), dtype=np.float64)
    particles: list[dict] = []

    x, y = w / 2.0, h / 2.0
    angle_deg = 0.0
    margin = float(cfg.particle_length_px)
    step_deg = np.degrees(cfg.angle_step_rad)
    area = float(np.pi * cfg.particle_length_px * cfg.particle_width_px / 4.0)

    for t in range(n):
        frame = background.copy()
        x += rng.normal(0.0, cfg.brownian_step_px)
        y += rng.normal(0.0, cfg.brownian_step_px)
        angle_deg += rng.normal(0.0, step_deg)
        x = float(min(max(x, margin), w - margin))
        y = float(min(max(y, margin), h - margin))
        peak = float(rng.uniform(180.0, 220.0))
        _render_ellipse(
            frame,
            x,
            y,
            angle_deg,
            float(cfg.particle_length_px),
            float(cfg.particle_width_px),
            peak,
        )
        frame += rng.normal(0.0, cfg.noise_sigma, size=(h, w))
        frames[t] = np.clip(frame, 0.0, 255.0)
        particles.append(
            {
                "id": 1,
                "x": x,
                "y": y,
                "angle": angle_deg,
                "length": float(cfg.particle_length_px),
                "width": float(cfg.particle_width_px),
                "area": area,
                "intensity": peak,
            }
        )

    ground_truth = {"n_molecules": 1, "particles": particles}
    return frames.astype(np.uint8), ground_truth

