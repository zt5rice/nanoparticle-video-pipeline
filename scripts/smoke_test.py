"""NumPy-only end-to-end smoke test: 40 frames, 1 molecule, pass_rate >= 0.99."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from nanotrack.config import PipelineConfig
from nanotrack.pipeline import run
from nanotrack.synth import generate


def main() -> None:
    cfg = PipelineConfig(n_frames=40, seed=0, backend="numpy")
    frames, gt = generate(cfg)
    result = run(frames, cfg, gt)
    rate = result["quality"]["pass_rate"]
    ok = rate >= 0.99 and result["n_tracks"] == 1

    out = Path(__file__).resolve().parents[1] / "output"
    out.mkdir(exist_ok=True)
    (out / "result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")

    print(f"frames={result['n_frames']} detections={result['n_detections']} "
          f"tracks={result['n_tracks']} quality_pass_rate={rate:.4f}")
    if ok:
        print("SMOKE OK")
    else:
        print("SMOKE FAILED")
        raise SystemExit(1)


if __name__ == "__main__":
    main()

