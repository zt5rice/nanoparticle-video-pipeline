"""Pytest setup: point Airflow's home into a writable, gitignored directory."""

import os
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
AIRFLOW_HOME = REPO / ".airflow_home"
AIRFLOW_HOME.mkdir(parents=True, exist_ok=True)
(AIRFLOW_HOME / "logs").mkdir(parents=True, exist_ok=True)
os.environ.setdefault("AIRFLOW_HOME", str(AIRFLOW_HOME))

