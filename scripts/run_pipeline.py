"""CLI: run the nanotrack pipeline (synthetic or real video) -> output artifacts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import yaml

from nanotrack.config import BACKENDS, PipelineConfig
from nanotrack.export import detections_to_rows, read_detections_rows, track_to_rows, write_csv
from nanotrack.pipeline import run, run_from_detections
from nanotrack.synth import generate

DETECTION_COLUMNS = [
    "frame", "blob_id", "x_px", "y_px", "angle_deg", "angle_rad",
    "length_px", "width_px", "area", "eccentricity",
]
TRACK_COLUMNS = [
    "track_id", "frame", "x_px", "y_px", "x_um", "y_um", "angle_deg",
    "angle_rad", "length_px", "eccentricity", "area", "missing", "interpolated",
]


def _write_outputs(result_raw: dict, cfg: PipelineConfig, out: Path) -> None:
    """Write result.json (summary), raw CSVs, config.yaml, and ground truth."""
    out.mkdir(parents=True, exist_ok=True)
    # result.json keeps the documented summary contract (no raw arrays inside).
    result = {k: v for k, v in result_raw.items() if k not in ("detections", "track", "ground_truth")}
    (out / "result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    (out / "config.yaml").write_text(yaml.safe_dump(cfg.to_dict(), sort_keys=False), encoding="utf-8")
    if "detections" in result_raw:
        write_csv(
            out / "detections.csv",
            detections_to_rows(result_raw["detections"]),
            columns=DETECTION_COLUMNS,
        )
    if "track" in result_raw:
        write_csv(out / "tracks.csv", track_to_rows(result_raw["track"], cfg), columns=TRACK_COLUMNS)
    if result_raw.get("ground_truth") is not None:
        (out / "ground_truth.json").write_text(
            json.dumps(result_raw["ground_truth"], indent=2), encoding="utf-8"
        )


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
    ap.add_argument(
        "--resume",
        action="store_true",
        help="resume from an existing output/detections.csv (skip image analysis)",
    )
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

    out = Path(args.out)
    if args.resume:
        # Resume from saved detections: skip preprocessing + detection entirely.
        det_path = out / "detections.csv"
        if not det_path.exists():
            print(f"error: --resume requested but {det_path} not found", file=sys.stderr)
            raise SystemExit(1)
        # Reuse the config that produced the detections unless overridden.
        if not args.config and (out / "config.yaml").exists():
            cfg = PipelineConfig.from_yaml(out / "config.yaml")
            if args.backend:
                cfg.backend = args.backend
        blobs = read_detections_rows(det_path)
        cfg.n_frames = len(blobs)
        cfg.max_lag = min(50, max(1, cfg.n_frames // 2))
        result_raw = run_from_detections(blobs, cfg, ground_truth=None, raw=True)
    else:
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
        result_raw = run(frames, cfg, gt, raw=True)

    _write_outputs(result_raw, cfg, out)
    result = {k: v for k, v in result_raw.items() if k not in ("detections", "track", "ground_truth")}
    print(json.dumps({k: result[k] for k in ("n_frames", "n_detections", "n_tracks")}))
    print(f"quality_pass_rate: {result['quality']['pass_rate']}")
    print(f"wrote {out / 'result.json'}, detections.csv, tracks.csv, config.yaml")


if __name__ == "__main__":
    main()
