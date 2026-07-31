from __future__ import annotations

from datetime import timedelta

import pendulum
from airflow.datasets import Dataset
from airflow.decorators import dag
from airflow.operators.bash import BashOperator
from operators.docker_exec_operator import DockerExecOperator

LANDING_DATASET = Dataset("lakehouse://landing/open-meteo")
SPARK_CONTAINER = "lakehouse-data-pipeline-spark-iceberg-1"
DBT_BIN = "/opt/dbt-venv/bin/dbt"
DBT_PROJECT_DIR = "/opt/airflow/dbt"

default_args = {
    # Spark job failures are usually deterministic (bad data, schema
    # mismatch, OOM), not transient -- more automatic retries mostly just
    # delay a human noticing. One retry with a longer delay leaves room for
    # a transient S3/Iceberg throttling blip to clear without over-retrying
    # a real bug.
    "retries": 1,
    "retry_delay": timedelta(minutes=10),
}


@dag(
    dag_id="processing_dag",
    schedule=[LANDING_DATASET],
    start_date=pendulum.datetime(2026, 7, 1, tz="UTC"),
    catchup=False,
    default_args=default_args,
    tags=["processing", "spark", "iceberg"],
)
def processing_dag() -> None:
    bronze = DockerExecOperator(
        task_id="bronze",
        container_name=SPARK_CONTAINER,
        command=["spark-submit", "/home/iceberg/src/lakehouse/processing/bronze.py"],
    )
    silver = DockerExecOperator(
        task_id="silver",
        container_name=SPARK_CONTAINER,
        command=["spark-submit", "/home/iceberg/src/lakehouse/processing/silver.py"],
    )
    gold = DockerExecOperator(
        task_id="gold",
        container_name=SPARK_CONTAINER,
        command=["spark-submit", "/home/iceberg/src/lakehouse/processing/gold.py"],
    )
    # Second, independent path off Bronze: dbt models (via Trino) produce
    # their own dbt_silver/dbt_gold tables. Runs in-process in this
    # container (not DockerExecOperator -- dbt only needs network access to
    # Trino, which this container already has), as a sibling of
    # silver >> gold, not blocking or blocked by the PySpark chain.
    dbt_transform = BashOperator(
        task_id="dbt_transform",
        bash_command=(
            f"{DBT_BIN} run --project-dir {DBT_PROJECT_DIR} --profiles-dir {DBT_PROJECT_DIR} && "
            f"{DBT_BIN} test --project-dir {DBT_PROJECT_DIR} --profiles-dir {DBT_PROJECT_DIR}"
        ),
    )
    bronze >> silver >> gold
    bronze >> dbt_transform


processing_dag()
