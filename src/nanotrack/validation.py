"""Data-quality checks -> DataQualityReport(pass_rate)."""

from __future__ import annotations

from .config import PipelineConfig


def report(track: dict, blobs_per_frame: list[list[dict]], cfg: PipelineConfig) -> dict:
    """Return ``{"pass_rate": float, "checks": [{"name", "passed", "detail"}]}``."""
    n = max(1, cfg.n_frames)
    present = track["present_frames"]
    coverage = present / n
    checks: list[dict] = []

    # 1. frame coverage: enough frames and >=90% present
    cov_ok = present >= cfg.min_track_len and coverage >= 0.90
    checks.append(
        {
            "name": "frame_coverage",
            "passed": bool(cov_ok),
            "detail": f"present={present}/{n} coverage={coverage:.2f}",
        }
    )

    # 2. length sanity
    summary = track.get("summary")
    if summary is None:
        summary = {}
    lmean = summary.get("length_mean")
    len_ok = lmean is not None and cfg.min_feature_size <= lmean <= cfg.image_size
    checks.append(
        {
            "name": "length_sanity",
            "passed": bool(len_ok),
            "detail": f"length_mean={lmean}",
        }
    )

    # 3. MSD fit quality
    r2 = summary.get("msd_fit_r2")
    r2_ok = r2 is not None and r2 >= 0.7
    checks.append(
        {
            "name": "msd_fit_r2",
            "passed": bool(r2_ok),
            "detail": f"msd_fit_r2={r2}",
        }
    )

    # 4. single primary object: at most one blob per frame (tolerance 5%)
    multi = sum(1 for blobs in blobs_per_frame if len(blobs) > 1)
    single_ok = multi / n <= 0.05
    checks.append(
        {
            "name": "single_primary",
            "passed": bool(single_ok),
            "detail": f"multi_blob_frames={multi}/{n}",
        }
    )

    passed = sum(1 for c in checks if c["passed"])
    return {"pass_rate": passed / len(checks), "checks": checks}

