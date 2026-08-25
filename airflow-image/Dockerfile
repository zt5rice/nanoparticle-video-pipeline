FROM apache/airflow:2.9.3-python3.11

# nanotrack runtime dependencies (numpy, scipy, pandas, ...) required by the DAG.
COPY --chown=airflow:root requirements.txt /requirements.txt
RUN pip install --user --no-cache-dir -r /requirements.txt

# Build context is the repository root (see docker-compose.yml), so src/ and dags/
# are inside the context. The directory is named airflow-image (not airflow) to
# avoid shadowing the Airflow Python package.
COPY --chown=airflow:root src /opt/airflow/src
COPY --chown=airflow:root dags /opt/airflow/dags

ENV PYTHONPATH=/opt/airflow/src
