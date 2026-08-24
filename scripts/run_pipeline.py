"""CLI: run the nanotrack pipeline (synthetic or real video) -> output/result.json."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from nanotrack.config import BACKENDS, PipelineConfig
from nanotrack.pipeline import run
from nanotrack.synth import generate


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--backend", choices=list(BACKENDS), default=None)
    ap.add_argument("--config", default=None, help="YAML config (PipelineConfig fields)")
    ap.add_argument(
        "--input",
        default=None,
        help="real video file (.tif/.tiff/.nd2) to analyze instead of synthetic data",
    )
    ap.add_argument("--out", default="output", help="output directory (result.json)")
    ap.add_argument("--n-frames", type=int, default=None)
    ap.add_argument("--seed", type=int, default=None)
    args = ap.parse_args()

    if args.config:
        cfg = PipelineConfig.from_yaml(args.config)
        if args.backend:
            cfg.backend = args.backend
    else:
        cfg = PipelineConfig(backend=args.backend or "numpy")
    if args.n_frames:
        cfg.n_frames = args.n_frames
    if args.seed is not None:
        cfg.seed = args.seed
    cfg.out_dir = args.out

    gt = None
    if args.input:
        # Real video path: load the file and analyze the whole movie (or --n-frames).
        try:
            from nanotrack.io import load_video

            frames, _meta = load_video(args.input)
        except Exception as exc:  # noqa: BLE001 - CLI should surface a clean error
            print(f"error: failed to load {args.input!r}: {exc}", file=sys.stderr)
            raise SystemExit(1)
        if args.n_frames:
            cfg.n_frames = max(1, min(int(args.n_frames), frames.shape[0]))
        else:
            cfg.n_frames = frames.shape[0]
        # Re-derive max_lag for the actual number of frames.
        cfg.max_lag = min(50, max(1, cfg.n_frames // 2))
    else:
        frames, gt = generate(cfg)
    result = run(frames, cfg, gt)

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({k: result[k] for k in ("n_frames", "n_detections", "n_tracks")}))
    print(f"quality_pass_rate: {result['quality']['pass_rate']}")
    print(f"wrote {out / 'result.json'}")


if __name__ == "__main__":
    main()
