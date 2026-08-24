FROM apache/airflow:2.9.3-python3.11

# Mount the nanotrack source + DAGs into the Airflow image.
COPY --chown=airflow:root ../src /opt/airflow/src
COPY --chown=airflow:root ../dags /opt/airflow/dags

ENV PYTHONPATH=/opt/airflow/src

