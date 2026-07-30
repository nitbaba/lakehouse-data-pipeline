FROM apache/airflow:2.10.5-python3.12

COPY requirements.txt /requirements.txt
# Pinned via Airflow's own constraints file so the new deps (dlt, docker SDK,
# amazon provider) resolve to versions known-compatible with this Airflow
# version, rather than an unconstrained resolution that could drift.
RUN pip install --no-cache-dir \
    --constraint "https://raw.githubusercontent.com/apache/airflow/constraints-2.10.5/constraints-3.12.txt" \
    -r /requirements.txt
