FROM apache/airflow:2.9.3-python3.11

# DAG runtime dependencies only (slim on purpose — see requirements-airflow.txt).
# The image's `pip` wrapper refuses root, and --user installs are disabled inside
# its virtualenv, so install into a separate target dir as the airflow user.
USER root
COPY --chown=airflow:root requirements-airflow.txt /requirements-airflow.txt
RUN mkdir -p /opt/airflow/deps && chown -R airflow:root /opt/airflow/deps
USER airflow
RUN pip install --target=/opt/airflow/deps --no-cache-dir -r /requirements-airflow.txt

# Build context is the repository root (see docker-compose.yml), so src/ and dags/
# are inside the context. The directory is named airflow-image (not airflow) to
# avoid shadowing the Airflow Python package.
USER root
COPY --chown=airflow:root src /opt/airflow/src
COPY --chown=airflow:root dags /opt/airflow/dags
USER airflow

ENV PYTHONPATH=/opt/airflow/src:/opt/airflow/deps
