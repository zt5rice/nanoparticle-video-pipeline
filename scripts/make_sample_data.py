"""Write sample synthetic data: sample_data/frames.tif + sample_data/config.yaml."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import yaml
from tifffile import imwrite

from nanotrack.config import PipelineConfig
from nanotrack.synth import generate


def main() -> None:
    sample_dir = Path(__file__).resolve().parents[1] / "sample_data"
    sample_dir.mkdir(exist_ok=True)
    cfg = PipelineConfig(n_frames=40, seed=1, backend="numpy")
    frames, _gt = generate(cfg)
    imwrite(sample_dir / "frames.tif", frames)
    (sample_dir / "config.yaml").write_text(
        yaml.safe_dump(cfg.to_dict(), sort_keys=False), encoding="utf-8"
    )
    print(f"wrote {sample_dir / 'frames.tif'} ({frames.shape}) and config.yaml")


if __name__ == "__main__":
    main()

