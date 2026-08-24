FROM apache/airflow:2.9.3-python3.11

# Build context is the repository root (see docker-compose.yml), so src/ and dags/
# are inside the context.
COPY --chown=airflow:root src /opt/airflow/src
COPY --chown=airflow:root dags /opt/airflow/dags

ENV PYTHONPATH=/opt/airflow/src
