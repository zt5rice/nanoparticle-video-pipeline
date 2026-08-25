# nanotrack

Single-molecule nanoparticle video tracking pipeline (SPT), reimplemented from the
author's MATLAB methodology (see `docs/implementation-plan.md` for the decision-complete
spec).

## Overview

**nanotrack** is an end-to-end, single-molecule (SPT) nanoparticle video-tracking
pipeline, re-engineered from the author's MATLAB methodology into a modern Python
data-infrastructure stack — a working-experience project for a Software Development
Engineer specializing in data infrastructure.

- **Computer-vision core** — frame-accurate detection of fast-moving, flexible
  nanoparticles (nanorods, nanosheets, single-walled carbon nanotubes): connected
  components + moment-based ellipse features, three interchangeable preprocessing
  backends (NumPy reference / OpenCV / scikit-image), and mod-180° orientation
  unwrapping so vertical rods track stably without fake ±90° jumps.
- **Parallelism & HPC** — Dask chunked processing with a sequential fallback, plus a
  SLURM batch example that mirrors the original "15 hours → 30 minutes" cluster
  speedup for long (10k-frame) videos.
- **Serving & orchestration** — FastAPI REST API (`/analyze`, `/tracking`), an Airflow
  DAG (`generate → preprocess → detect_track → features_validate → export`), and a
  Docker Compose stack (API / Airflow / Postgres / Prometheus / Grafana).
- **Observability** — Prometheus metrics (frames analyzed, errors, runtime p95) with a
  provisioned Grafana `nanotrack-pipeline` dashboard.
- **Data engineering & reproducibility** — immutable per-run artifacts (raw per-frame
  `tracks.csv` / `detections.csv`, config + ground-truth provenance), checkpoint
  resume (`--resume`), self-contained tracking-QC HTML reports, and tracking-overlay
  videos for visual QA.
- **CI/CD & delivery** — GitHub Actions CI (ruff, pytest, smoke) plus a Docker
  end-to-end job that boots the full stack and validates the Airflow DAG.
- **Research impact** — methods support 12 peer-reviewed publications, including
  ACS Nano and Soft Matter.

The pipeline ships as the `nanotrack` Python package with a CLI, REST API, and
ImageJ-style preprocessing notebook — usable end-to-end on synthetic data or real
fluorescence videos (TIFF / ND2).

> `ref/` (papers + MATLAB source) is local-only and not part of the repository.

## Quick start

```bash
make venv && make install   # create .venv and install dependencies
make smoke                  # end-to-end smoke test (40 frames, 1 molecule)
make sample && make run     # write sample data and run the pipeline
python scripts/run_pipeline.py --input video.tif --out output   # analyze a real video
python scripts/run_pipeline.py --out output --resume            # rebuild from detections.csv
python scripts/run_pipeline.py --input video.tif --out output --overlay  # + trajectory overlay video
```

Each run also writes `output/tracking_report.html` — a self-contained tracking-QC
dashboard (trajectory, x/y vs frame, angle vs frame, MSD). With the API up, open
`http://localhost:8000/tracking`.

### Docker stack (local)

```bash
mkdir -p output && chmod -R 777 output   # Airflow runs as a non-root user
docker compose up --build
```

Services: API `:8000`, Airflow `:8080`, Prometheus `:9090`, Grafana `:3000`.

## Example outputs

**Tracking QC report** — an interactive HTML report is written to
`output/tracking_report.html` after every run (trajectory overlaid on the first frame,
x/y vs frame, unwrapped angle in deg vs frame, MSD vs lag). Static preview:

![Tracking QC report](docs/assets/tracking_qc_preview.png)

**Tracking overlay video** — `--overlay` draws the tracked trajectory and orientation
onto the input video (`output/tracking_overlay.mp4`, or `.gif` / `.png` via
`--overlay-format`). Example on a single-molecule (vertical-rod) video:

![Tracking overlay on a single-molecule video](docs/assets/tracking_overlay.gif)

## Citation

If you use this tool in your work, please cite the methodology paper:

> Z. Tang, S. L. Eichmann, B. Lounis, L. Cognet, F. C. MacKintosh, M. Pasquali,
> *Single-walled carbon nanotube reptation dynamics in submicron sized pores from
> randomly packed mono-sized colloids*, Soft Matter **2022**.
> DOI: [10.1039/D2SM00305H](https://doi.org/10.1039/D2SM00305H)

## Layout

```
src/nanotrack/   core package
scripts/         CLI entrypoints
tests/           pytest suite
docs/            implementation plan + system design
```
