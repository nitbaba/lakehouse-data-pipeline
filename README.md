# Lakehouse Data Pipeline

Open-source, code-first data lakehouse: dlt, Apache Iceberg, AWS S3, PySpark, Apache Airflow, and Great Expectations, governed with Terraform, Docker, and GitHub Actions CI/CD. See [plan.md](plan.md) for the full roadmap.

## Phase 1: Local Environment

### Prerequisites
Docker, Docker Compose, Terraform, AWS CLI, Python 3.12+, and working AWS credentials (`aws sts get-caller-identity`).

### Setup

```bash
make init          # venv, dev deps, pre-commit hooks, .env / terraform.tfvars from examples
make tf-init
make tf-plan
make tf-apply       # creates the S3 bucket + IAM role in your AWS account
make tf-output       # note the iam_role_arn output
```

Add the pipeline role as an assumable AWS CLI profile in `~/.aws/config`:

```ini
[profile lakehouse-pipeline]
role_arn = <iam_role_arn from terraform output>
source_profile = default
region = us-east-1
```

Then set `LAKEHOUSE_BUCKET_NAME` in `.env` to the `bucket_id` from `make tf-output`, and start the stack:

```bash
make up
make ps
```

- Airflow UI: http://localhost:8081 (login: `AIRFLOW_ADMIN_USERNAME` / `AIRFLOW_ADMIN_PASSWORD` from `.env`)
- Spark / Jupyter: http://localhost:8888 (token: `JUPYTER_TOKEN` from `.env`)
- Spark UI: http://localhost:8082
- Iceberg REST catalog: http://localhost:8181/v1/config

### Everyday commands

```bash
make fmt          # format Python + Terraform
make lint         # ruff + mypy + terraform validate
make test         # pytest
make down         # stop the stack
```

## Phase 2: Ingestion (dlt)

A standalone dlt pipeline (`src/lakehouse/ingestion/`) ingests daily historical weather data from the [Open-Meteo archive API](https://open-meteo.com/) for a few hardcoded locations into the S3 landing zone (`s3://<bucket>/landing/open_meteo/`), one dlt resource per location with its own incremental date cursor.

```bash
make ingest        # runs the pipeline against the real S3 bucket in .env
```

Reruns only fetch dates since the last load — a same-day rerun does no work and lands no new files.

## Phase 3: Storage & Processing (Iceberg + PySpark)

A Bronze -> Silver -> Gold pipeline (`src/lakehouse/processing/`) runs inside the `spark-iceberg` container against the real Iceberg REST catalog:

- **Bronze** (`rest.bronze.weather_daily_raw`): raw landing JSON read via Spark's Hadoop S3A connector, full overwrite each run (landing is append-only across dlt runs, so this is the simplest correctly-idempotent approach).
- **Silver** (`rest.silver.weather_daily`): deduplicated, typed, `MERGE INTO`-based on `(date, location)`.
- **Gold** (`rest.gold.monthly_location_climate_summary`): monthly per-location climate aggregates, full recompute.
- **Maintenance**: Iceberg compaction (`rewrite_data_files`) and snapshot expiration (`expire_snapshots`, 7-day / last-5 retention) on all three tables.

```bash
make spark-medallion     # bronze -> silver -> gold
make spark-maintenance   # compaction + snapshot expiration
```

Spark's Hadoop S3A connector (needed for the raw Bronze read — a different code path from Iceberg's own S3FileIO used everywhere else) can't resolve this project's assumable-role AWS profile on its own; job code assumes the role itself via boto3 and hands Spark temporary credentials (see `src/lakehouse/processing/spark_session.py`).

## Phase 4: Data Quality & Testing

Great Expectations validates data in-line with the real pipeline (`src/lakehouse/quality/expectations.py`) — `validate_landing()` runs on the raw Bronze read (structural checks, known locations, plausible temperature/precipitation ranges), `validate_silver()` runs on the deduplicated Silver data (adds `(date, location)` uniqueness and a `temperature_max >= temperature_min` cross-column check). Either raises on failure, same as this pipeline's existing "fail loud" pattern elsewhere.

`src/lakehouse/processing/{silver,gold}.py` expose their transformation logic as pure, catalog-free functions (`dedupe_bronze()`, `compute_monthly_summary()`), tested offline against local PySpark fixtures (Java 17 + a `local[1]` SparkSession, no Docker/AWS needed):

```bash
make test    # includes tests/test_processing_*.py and tests/test_quality_expectations.py
```

## Phase 5: Orchestration (Airflow)

Two DAGs, linked by an Airflow Dataset rather than a fixed time offset:

- **`ingestion_dag`** (`@daily`) — runs `lakehouse.ingestion.pipeline.run()` in-process inside Airflow's own container (dlt is installed there now), reading the `aws_lakehouse` Airflow Connection (`profile_name`/`region_name`, no static keys — same assumable-role pattern as everywhere else in this project) instead of a bare env var. On success it marks the `lakehouse://landing/open-meteo` dataset updated.
- **`processing_dag`** (triggered by that dataset, not a cron schedule) — three sequential tasks (`bronze >> silver >> gold`) using a custom `DockerExecOperator` (`src/lakehouse/orchestration/docker_exec.py` + `dags/operators/docker_exec_operator.py`) that execs the existing `spark-submit .../bronze.py` etc. commands inside the already-running `spark-iceberg` container — the same commands `make spark-bronze` etc. already run manually.

The `airflow-scheduler` container mounts `/var/run/docker.sock` (and runs as root, since Airflow's default non-root user can't read that root-owned socket) to make the `DockerExecOperator` possible — accepted tradeoff: this gives the scheduler host-root-equivalent access via the Docker daemon. Retries and an SLA are set per-DAG: `ingestion_dag` gets a real SLA (`sla_miss_callback` logs a warning) since it's schedule-driven; `processing_dag`'s dataset-triggered runs aren't SLA-checked by Airflow at all (2.10.5's documented behavior), so it relies on `retries` + the operator's `AirflowException` on failure instead.

```bash
make up                                    # brings up the whole stack including Airflow
# in the Airflow UI (localhost:8081) or via CLI:
airflow dags unpause ingestion_dag processing_dag
airflow dags trigger ingestion_dag         # manual run; @daily handles the rest
```

## Phase 7: Analytics & Visualization (Trino + Superset)

[Trino](https://trino.io/) queries the Gold Iceberg table directly through the same REST catalog Spark uses (`docker/trino/catalog/iceberg.properties`), no separate sync/export step. [Apache Superset](https://superset.apache.org/) connects to Trino as its SQL source; its own metadata store is a second database (`superset`) on the same shared `postgres` container Airflow already uses (`docker/postgres/init/`'s multi-database init script), not a new Postgres instance.

`superset-init` runs Superset's one-time `db upgrade` / admin-user / `init` bootstrap (mirroring `airflow-init`) before the `superset` webserver starts.

```bash
make up     # also brings up trino, superset-init, and superset
```

Verify Trino can read the Gold table directly, without going through Superset:

```bash
docker compose exec trino trino --catalog iceberg --execute "SELECT * FROM gold.monthly_location_climate_summary LIMIT 5"
```

Then, one-time manual setup in Superset (no scripted equivalent — this is normally a UI-driven step for a real analyst too):

1. Log into Superset at http://localhost:8088 (`SUPERSET_ADMIN_USERNAME` / `SUPERSET_ADMIN_PASSWORD` from `.env`).
2. Settings → Database Connections → **+ Database** → SQLAlchemy URI: `trino://superset@trino:8080/iceberg`.
3. Add a dataset for `gold.monthly_location_climate_summary`, then build a chart and save it to a dashboard.
