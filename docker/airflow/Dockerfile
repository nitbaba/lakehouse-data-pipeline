FROM apache/airflow:2.10.5-python3.12

COPY requirements.txt /requirements.txt
# Pinned via Airflow's own constraints file so the new deps (dlt, docker SDK,
# amazon provider) resolve to versions known-compatible with this Airflow
# version, rather than an unconstrained resolution that could drift.
RUN pip install --no-cache-dir \
    --constraint "https://raw.githubusercontent.com/apache/airflow/constraints-2.10.5/constraints-3.12.txt" \
    -r /requirements.txt

# dbt-core pins its own versions of common libraries (click, jinja2,
# protobuf, etc.) that can collide with Airflow's own constraint-pinned
# versions above, so it gets an isolated venv instead of joining Airflow's
# site-packages. The base image's default user (non-root "airflow") can't
# write to /opt, and this same image is shared by airflow-init and
# airflow-webserver too -- switch to root only for this step, then back,
# so their default (non-root) runtime user is unaffected.
USER root
# git: dbt's own `dbt debug` dependency check expects it (used for
# git-based packages via `dbt deps`, which this project doesn't use, but
# its absence still shows as a failed check otherwise).
RUN apt-get update && \
    apt-get install -y --no-install-recommends git && \
    rm -rf /var/lib/apt/lists/*
RUN python3 -m venv /opt/dbt-venv && \
    /opt/dbt-venv/bin/pip install --no-cache-dir dbt-trino==1.10.3
USER airflow
