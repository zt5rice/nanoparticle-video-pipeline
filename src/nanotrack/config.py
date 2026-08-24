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

    backend: str = "numpy"
    image_size: int = 512
    n_frames: int = 40
    threshold_mult: float = 3.0
    min_feature_size: int = 10
    max_disp: float = 10.0
    min_track_len: int = 20
    memory: int = 3
    fps: float = 16.75
    dt: float = 1.0 / 16.75
    pixels_per_micron: float = 0.302
    noise_sigma: float = 8.0
    background_strength: float = 20.0
    particle_length_px: int = 40
    particle_width_px: int = 6
    brownian_step_px: float = 0.5
    angle_step_rad: float = 0.03
    max_lag: int | None = None
    msd_fit_frac: float = 0.25
    msd_n_lags: int = 40
    chunk_size: int = 16
    dask_scheduler: str = "threads"
    seed: int = 0
    out_dir: str = "output"
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
