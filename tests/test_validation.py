"""Data-quality report tests: pass/fail behavior of each check."""

from nanotrack.config import PipelineConfig
from nanotrack.validation import report


def _track(present, n_frames, summary):
    """Minimal track stub with only the fields report() needs."""
    return {
        "present_frames": present,
        "valid": present >= 5,
        "summary": summary,
        "frames": [],
    }


def test_valid_report_passes_all():
    """A complete, well-formed track passes every check (pass_rate = 1.0)."""
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
    """A track present in only 5/40 frames fails the frame-coverage check."""
    cfg = PipelineConfig(n_frames=40, min_track_len=20)
    trk = _track(5, 40, {"length_mean": 40.0, "msd_fit_r2": 0.9})
    bpf = [[{"x": 0, "y": 0}]] * 40
    r = report(trk, bpf, cfg)
    assert r["checks"][0]["passed"] is False
    assert r["pass_rate"] < 1.0


def test_multi_blob_flag():
    """Frames with >1 blob exceed the 5% tolerance -> single_primary check fails."""
    cfg = PipelineConfig(n_frames=10, min_track_len=5)
    trk = _track(10, 10, {"length_mean": 40.0, "msd_fit_r2": 0.9})
    bpf = [[{"x": 0, "y": 0}, {"x": 5, "y": 5}]] * 10
    r = report(trk, bpf, cfg)
    assert r["checks"][3]["passed"] is False


def test_single_primary_ok():
    """Frames with exactly one blob pass the single_primary check."""
    cfg = PipelineConfig(n_frames=10, min_track_len=5)
    trk = _track(10, 10, {"length_mean": 40.0, "msd_fit_r2": 0.9})
    bpf = [[{"x": 0, "y": 0}]] * 10
    r = report(trk, bpf, cfg)
    assert r["checks"][3]["passed"] is True
