FROM apache/airflow:2.9.3-python3.11

# nanotrack runtime dependencies (numpy, scipy, pandas, ...) required by the DAG.
USER root
COPY --chown=airflow:root requirements.txt /requirements.txt
RUN pip install --no-cache-dir -r /requirements.txt
USER airflow

# Build context is the repository root (see docker-compose.yml), so src/ and dags/
# are inside the context. The directory is named airflow-image (not airflow) to
# avoid shadowing the Airflow Python package.
COPY --chown=airflow:root src /opt/airflow/src
COPY --chown=airflow:root dags /opt/airflow/dags

ENV PYTHONPATH=/opt/airflow/src
