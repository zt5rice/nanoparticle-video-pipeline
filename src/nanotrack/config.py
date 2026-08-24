"""Pipeline configuration."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import yaml

BACKENDS = ("numpy", "opencv", "skimage")


@dataclass
class PipelineConfig:
    """Decision-complete pipeline configuration (see docs/implementation-plan.md)."""

    # --- Backend / dispatch ---
    # Preprocessing backend. "numpy" is the faithful MATLAB port (reference);
    # "opencv" / "skimage" are added in Phase 2.
    backend: str = "numpy"

    # --- Video / imaging setup ---
    # Square frame size in pixels.
    image_size: int = 512
    # Number of frames per video.
    n_frames: int = 40
    # Acquisition frame rate (frames/s).
    fps: float = 16.75
    # Time step per frame (s); recomputed from fps in __post_init__.
    dt: float = 1.0 / 16.75
    # Pixel-to-micron calibration (100x NIR setting).
    pixels_per_micron: float = 0.302

    # --- Synthetic data generation ---
    # Gaussian noise standard deviation (8-bit image).
    noise_sigma: float = 8.0
    # Amplitude of the smooth background gradient.
    background_strength: float = 20.0
    # Ellipse major-axis length (px) of the synthetic molecule.
    particle_length_px: int = 40
    # Ellipse minor-axis length (px) of the synthetic molecule.
    particle_width_px: int = 6
    # COM random-walk step sigma (px/frame).
    brownian_step_px: float = 0.5
    # Angle random-walk step sigma (rad/frame).
    angle_step_rad: float = 0.03
    # Initial orientation of the synthetic rod (deg); e.g. 90 for a vertical rod.
    initial_angle_deg: float = 0.0
    # RNG seed for reproducible synthetic videos.
    seed: int = 0

    # --- Detection ---
    # MATLAB bpassSWNT "stdThreshold" multiplier for the global threshold.
    threshold_mult: float = 3.0
    # Masscut: minimum bbox-extent sum (px) for a component to be kept.
    min_feature_size: int = 10

    # --- Tracking (SPT) ---
    # Max displacement (px) to link a blob to the single track.
    max_disp: float = 10.0
    # Minimum number of present frames for a valid track.
    min_track_len: int = 20
    # Max consecutive missing frames back-filled by linear interpolation.
    memory: int = 3

    # --- Feature analysis (MSD/MSAD) ---
    # Max lag in frames; default min(50, n_frames // 2).
    max_lag: int | None = None
    # Fraction of leading lags used for the linear fit (Dt / Dr).
    msd_fit_frac: float = 0.25
    # Number of log-spaced lag points (fast MSD/MSAD for long videos).
    msd_n_lags: int = 40

    # --- Parallelism ---
    # Chunk size for the Dask chunk map.
    chunk_size: int = 16
    # Dask scheduler: "threads" | "processes" | "single-threaded".
    dask_scheduler: str = "threads"

    # --- Output ---
    # Directory for result.json / exports.
    out_dir: str = "output"
    # Fixed SPT scope: exactly one molecule per field of view.
    n_molecules: int = field(default=1, repr=False)

    def __post_init__(self) -> None:
        if self.backend not in BACKENDS:
            raise ValueError(f"backend must be one of {BACKENDS}, got {self.backend!r}")
        if self.n_molecules != 1:
            raise ValueError("single-molecule scope: n_molecules must be 1")
        if self.fps and self.fps > 0:
            self.dt = 1.0 / self.fps
        if self.max_lag is None:
            self.max_lag = min(50, max(1, self.n_frames // 2))
        else:
            self.max_lag = max(1, int(self.max_lag))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_yaml(cls, path: str | Path) -> PipelineConfig:
        data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
