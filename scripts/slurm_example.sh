#!/usr/bin/env bash
#
# Example SLURM job: batch-parallel nanoparticle video analysis with nanotrack.
#
# Mirrors the "15 hours -> 30 minutes" narrative: each video is analyzed
# independently, so videos are spread across SLURM array tasks (or GNU parallel)
# instead of being processed serially.
#
# Usage (on an HPC login node):
#   sbatch scripts/slurm_example.sh            # run the job array
#   sbatch --array=1-24 scripts/slurm_example.sh   # 24 videos, 1 per task
#
# Adjust the paths below to your cluster environment.

#SBATCH --job-name=nanotrack
#SBATCH --output=logs/nanotrack_%A_%a.out
#SBATCH --error=logs/nanotrack_%A_%a.err
#SBATCH --array=1-4
#SBATCH --cpus-per-task=4
#SBATCH --mem=8G
#SBATCH --time=00:30:00

set -euo pipefail

# --- Environment (adapt to your cluster) ---
REPO_DIR="${REPO_DIR:-$HOME/nanotrack}"
VENV_BIN="${VENV_BIN:-$REPO_DIR/.venv/bin}"
DATA_DIR="${DATA_DIR:-$REPO_DIR/data/videos}"   # contains video_001.tif ...
OUT_ROOT="${OUT_ROOT:-$REPO_DIR/output}"

mkdir -p "$OUT_ROOT" logs

# --- Pick the video for this array task ---
VIDEO="$(printf '%s/video_%03d.tif' "$DATA_DIR" "$SLURM_ARRAY_TASK_ID")"
if [[ ! -f "$VIDEO" ]]; then
  echo "video not found: $VIDEO" >&2
  exit 1
fi

echo "task=$SLURM_ARRAY_TASK_ID analyzing $VIDEO"

# --- Analyze one video (single-molecule SPT, NumPy backend) ---
# Each task writes its own result file so tasks never contend on shared output.
"$VENV_BIN/python" "$REPO_DIR/scripts/run_pipeline.py" \
  --backend numpy \
  --out "$OUT_ROOT/$(basename "$VIDEO" .tif)"

echo "done: $OUT_ROOT/$(basename "$VIDEO" .tif)/result.json"

# For even more parallelism, swap the array loop for GNU parallel:
#   find "$DATA_DIR" -name '*.tif' | parallel -j "$SLURM_CPUS_PER_TASK" \
#     "$VENV_BIN/python" "$REPO_DIR/scripts/run_pipeline.py" --out "$OUT_ROOT/{/.}" -- {}
