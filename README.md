# Lakehouse Data Pipeline

[![Lint and Test](https://github.com/nitbaba/lakehouse-data-pipeline/actions/workflows/lint-and-test.yml/badge.svg)](https://github.com/nitbaba/lakehouse-data-pipeline/actions/workflows/lint-and-test.yml)
[![Terraform CI](https://github.com/nitbaba/lakehouse-data-pipeline/actions/workflows/terraform-ci.yml/badge.svg)](https://github.com/nitbaba/lakehouse-data-pipeline/actions/workflows/terraform-ci.yml)
[![Docker Build and Scan](https://github.com/nitbaba/lakehouse-data-pipeline/actions/workflows/docker-build.yml/badge.svg)](https://github.com/nitbaba/lakehouse-data-pipeline/actions/workflows/docker-build.yml)

Open-source, code-first data lakehouse: dlt, Apache Iceberg, AWS S3, PySpark, Apache Airflow, and Great Expectations, governed with Terraform, Docker, and GitHub Actions CI/CD. See [plan.md](plan.md) for the full roadmap.

## Architecture

A `dlt` pipeline lands raw weather data in S3, and PySpark builds a Bronze → Silver → Gold medallion on Iceberg, checked along the way by Great Expectations and orchestrated by Airflow. Trino and Superset then serve the Gold layer as dashboards, and Terraform, Docker Compose, and GitHub Actions provision, run, and gate all of it. For the full lineage diagram and a layer-by-layer walkthrough, see [docs/architecture.md](docs/architecture.md).

| Layer | Technology |
| :--- | :--- |
| Cloud / IaC | Terraform, AWS S3, IAM |
| Ingestion | dlt |
| Storage / Table Format | Apache Iceberg (REST catalog) |
| Processing | PySpark |
| Orchestration | Apache Airflow |
| Data Quality | Great Expectations |
| Query Engine | Trino |
| Visualization | Apache Superset |
| CI/CD | GitHub Actions |

## Repository Layout

```
src/lakehouse/       # ingestion, processing (bronze/silver/gold), quality, orchestration code
dags/                # Airflow DAGs (ingestion_dag, processing_dag) + custom operators
docker/              # per-service Dockerfiles/config: airflow, spark, postgres, trino, superset
terraform/           # S3 bucket, pipeline IAM role, GitHub Actions OIDC role
great_expectations/  # data quality suites
tests/               # pytest suites (local PySpark fixtures, no Docker/AWS needed)
docs/                # architecture documentation
.github/workflows/   # lint-and-test, terraform-ci, docker-build CI pipelines
```

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

Reruns only fetch dates since the last load, so running it again the same day does no work and lands no new files.

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

Spark's Hadoop S3A connector, needed for the raw Bronze read and a different code path from the Iceberg S3FileIO used everywhere else, can't resolve this project's assumable-role AWS profile on its own. So the job code assumes the role itself via boto3 and hands Spark ready-made temporary credentials (see `src/lakehouse/processing/spark_session.py`).

## Phase 4: Data Quality & Testing

Great Expectations validates data in-line with the real pipeline (`src/lakehouse/quality/expectations.py`). `validate_landing()` runs on the raw Bronze read, checking structure, known locations, and plausible temperature and precipitation ranges. `validate_silver()` runs on the deduplicated Silver data and adds a `(date, location)` uniqueness check plus a `temperature_max >= temperature_min` cross-column check. Both raise on failure, matching this pipeline's fail-loud pattern everywhere else.

`src/lakehouse/processing/{silver,gold}.py` expose their transformation logic as pure, catalog-free functions (`dedupe_bronze()`, `compute_monthly_summary()`), tested offline against local PySpark fixtures (Java 17 + a `local[1]` SparkSession, no Docker/AWS needed):

```bash
make test    # includes tests/test_processing_*.py and tests/test_quality_expectations.py
```

## Phase 5: Orchestration (Airflow)

Two DAGs, linked by an Airflow Dataset rather than a fixed time offset:

- **`ingestion_dag`** (`@daily`) runs `lakehouse.ingestion.pipeline.run()` in-process inside Airflow's own container (dlt is installed there now). It reads AWS credentials from the `aws_lakehouse` Airflow Connection (`profile_name`/`region_name`, the same assumable-role pattern used everywhere else in this project) instead of a bare env var, and marks the `lakehouse://landing/open-meteo` dataset updated once it succeeds.
- **`processing_dag`** is triggered by that dataset rather than a cron schedule, and runs three sequential tasks (`bronze >> silver >> gold`) through a custom `DockerExecOperator` (`src/lakehouse/orchestration/docker_exec.py` + `dags/operators/docker_exec_operator.py`). It execs the same `spark-submit .../bronze.py` etc. commands that `make spark-bronze` and friends already run manually, inside the already-running `spark-iceberg` container.

The `airflow-scheduler` container mounts `/var/run/docker.sock` and runs as root, since Airflow's default non-root user can't read that root-owned socket, to make the `DockerExecOperator` possible. That's an accepted tradeoff: it gives the scheduler host-root-equivalent access through the Docker daemon. Retries and an SLA are set per DAG. `ingestion_dag` gets a real SLA (`sla_miss_callback` logs a warning) since it's schedule-driven, while `processing_dag`'s dataset-triggered runs aren't SLA-checked by Airflow at all (documented behavior in 2.10.5), so it relies on `retries` plus the operator's `AirflowException` on failure instead.

```bash
make up                                    # brings up the whole stack including Airflow
# in the Airflow UI (localhost:8081) or via CLI:
airflow dags unpause ingestion_dag processing_dag
airflow dags trigger ingestion_dag         # manual run; @daily handles the rest
```

## Phase 6: CI/CD (GitHub Actions)

Three workflows, all in `.github/workflows/`:

- **`lint-and-test.yml`** runs `ruff check`, `ruff format --check`, `mypy`, and `pytest`, each as its own step rather than one `make lint` call, so a failure is individually attributable in the GitHub UI. It runs on every push to `master` and every PR, and never touches AWS credentials.
- **`terraform-ci.yml`** has two jobs. `fmt-validate` (`terraform fmt -check`, `init`, `validate`) needs no AWS credentials at all, since state is local-only with no backend, and runs on every push, PR, and dispatch. `plan` runs `terraform plan` against real AWS, authenticated through a narrowly-scoped, read-only IAM role assumed via GitHub's OIDC federation (`terraform/modules/github_actions_role/`), so there are no static keys stored anywhere. It only runs on a push to `master` or a manual `workflow_dispatch`, **never on `pull_request`**, so the OIDC-assumable role is never reachable from an untrusted fork PR.
- **`docker-build.yml`** builds the `airflow` and `spark` images in a matrix and scans each with [Trivy](https://trivy.dev/) in report-only mode (`exit-code: "0"`, since this project doesn't control CVEs in the upstream base images), uploading the SARIF results to the repo's Security → Code Scanning tab.

For the `plan` job to succeed, the corresponding Terraform (`module.github_actions_ci` in `terraform/main.tf`) has to already exist and be applied, with its ARN published as the `LAKEHOUSE_TF_CI_ROLE_ARN` GitHub Actions repository variable. That's a one-time setup step done by hand, not something CI can bootstrap for itself.

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

Then there's a one-time manual setup step in Superset. There's no scripted equivalent for this, since it's normally a UI-driven step for a real analyst too:

1. Log into Superset at http://localhost:8088 (`SUPERSET_ADMIN_USERNAME` / `SUPERSET_ADMIN_PASSWORD` from `.env`).
2. Settings → Database Connections → **+ Database** → SQLAlchemy URI: `trino://superset@trino:8080/iceberg`.
3. Add a dataset for `gold.monthly_location_climate_summary`, then build a chart and save it to a dashboard.
