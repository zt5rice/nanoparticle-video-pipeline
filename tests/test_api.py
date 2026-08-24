"""API tests: /health, /analyze, /metrics, /tracking."""

from fastapi.testclient import TestClient

from nanotrack.api import app
from nanotrack.config import PipelineConfig
from nanotrack.pipeline import run
from nanotrack.report import write_tracking_report
from nanotrack.synth import generate

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_analyze_valid():
    r = client.post("/analyze", json={"n_frames": 60, "backend": "numpy"})
    assert r.status_code == 200
    body = r.json()
    assert body["n_tracks"] == 1
    assert body["quality_pass_rate"] >= 0.99
    assert body["tracks"][0]["track_id"] == 1


def test_analyze_invalid_input():
    r = client.post("/analyze", json={"n_frames": 5, "backend": "numpy"})
    assert r.status_code == 422
    r = client.post("/analyze", json={"n_frames": 60, "backend": "nope"})
    assert r.status_code == 422


def test_metrics():
    r = client.get("/metrics")
    assert r.status_code == 200
    assert "nanotrack_frames_total" in r.text


def test_tracking_page(tmp_path):
    cfg = PipelineConfig(image_size=128, n_frames=10, seed=0, min_track_len=3)
    frames, _ = generate(cfg)
    result = run(frames, cfg, raw=True)
    write_tracking_report(result, cfg, tmp_path / "tracking_report.html", frames)

    ok = client.get("/tracking", params={"out": str(tmp_path)})
    assert ok.status_code == 200
    assert "text/html" in ok.headers["content-type"]

    missing = client.get("/tracking", params={"out": str(tmp_path / "nope")})
    assert missing.status_code == 404

