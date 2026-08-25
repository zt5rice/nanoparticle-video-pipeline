"""Airflow DAG parse test (skipped when airflow is not installed)."""

import importlib.util
from pathlib import Path

import pytest

# Skip when the real Airflow package is unavailable (CI without airflow, or when
# a local directory shadows the package name). Importing a submodule guards
# against namespace-package shadowing.
pytest.importorskip("airflow.operators.python")

DAG_FILE = Path(__file__).resolve().parents[1] / "dags" / "nanoparticle_pipeline.py"


def _load_dag():
    spec = importlib.util.spec_from_file_location("nanoparticle_pipeline", DAG_FILE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.dag


def test_dag_parses_with_expected_tasks():
    dag = _load_dag()
    assert dag.dag_id == "nanoparticle_video_pipeline"
    assert set(dag.task_ids) == {
        "generate",
        "preprocess",
        "detect_track",
        "features_validate",
        "export",
    }
