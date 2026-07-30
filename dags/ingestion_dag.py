from __future__ import annotations

import logging
import os
from datetime import timedelta
from typing import Any

import pendulum
from airflow.datasets import Dataset
from airflow.decorators import dag, task

log = logging.getLogger(__name__)

# Dataset URIs are just identifiers to Airflow -- they don't need to resolve
# to anything real -- so this is a stable logical name, not tied to the
# actual LAKEHOUSE_BUCKET_NAME at DAG-parse time.
LANDING_DATASET = Dataset("lakehouse://landing/open-meteo")


def _sla_miss_callback(*args: Any, **kwargs: Any) -> None:
    log.error("SLA missed for ingestion_dag's run_dlt_ingestion task")


default_args = {
    # External-API flakiness (Open-Meteo) is the realistic failure mode here,
    # not deterministic bugs -- a couple of retries with a short backoff is
    # standard for tasks calling third-party APIs.
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}


@dag(
    dag_id="ingestion_dag",
    schedule="@daily",
    start_date=pendulum.datetime(2026, 7, 1, tz="UTC"),
    catchup=False,
    default_args=default_args,
    sla_miss_callback=_sla_miss_callback,
    tags=["ingestion", "dlt"],
)
def ingestion_dag() -> None:
    # Airflow 2.10.5 does not check SLAs on manually-triggered or dataset-
    # triggered ("event-driven") DAG runs -- only real schedule-driven runs
    # like this DAG's @daily. See docker-compose.yml / plan notes.
    @task(outlets=[LANDING_DATASET], sla=timedelta(minutes=20))
    def run_dlt_ingestion() -> None:
        from airflow.hooks.base import BaseHook

        from lakehouse.ingestion.pipeline import run

        conn = BaseHook.get_connection("aws_lakehouse")
        extra = conn.extra_dejson
        if profile := extra.get("profile_name"):
            os.environ["AWS_PROFILE"] = profile
        if region := extra.get("region_name"):
            os.environ.setdefault("AWS_REGION", region)
        run()

    run_dlt_ingestion()


ingestion_dag()
