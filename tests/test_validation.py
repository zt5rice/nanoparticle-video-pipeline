from nanotrack.config import PipelineConfig
from nanotrack.validation import report


def _track(present, n_frames, summary):
    return {
        "present_frames": present,
        "valid": present >= 5,
        "summary": summary,
        "frames": [],
    }


def test_valid_report_passes_all():
    cfg = PipelineConfig(n_frames=40, min_track_len=20)
    trk = _track(
        40,
        40,
        {"length_mean": 40.0, "msd_fit_r2": 0.9},
    )
    bpf = [[{"x": 0, "y": 0}]] * 40
    r = report(trk, bpf, cfg)
    assert r["pass_rate"] == 1.0


def test_low_coverage_fails():
    cfg = PipelineConfig(n_frames=40, min_track_len=20)
    trk = _track(5, 40, {"length_mean": 40.0, "msd_fit_r2": 0.9})
    bpf = [[{"x": 0, "y": 0}]] * 40
    r = report(trk, bpf, cfg)
    assert r["checks"][0]["passed"] is False
    assert r["pass_rate"] < 1.0


def test_multi_blob_flag():
    cfg = PipelineConfig(n_frames=10, min_track_len=5)
    trk = _track(10, 10, {"length_mean": 40.0, "msd_fit_r2": 0.9})
    bpf = [[{"x": 0, "y": 0}, {"x": 5, "y": 5}]] * 10
    r = report(trk, bpf, cfg)
    assert r["checks"][3]["passed"] is False  # 10/10 multi-blob frames exceeds 5%


def test_single_primary_ok():
    cfg = PipelineConfig(n_frames=10, min_track_len=5)
    trk = _track(10, 10, {"length_mean": 40.0, "msd_fit_r2": 0.9})
    bpf = [[{"x": 0, "y": 0}]] * 10
    r = report(trk, bpf, cfg)
    assert r["checks"][3]["passed"] is True
