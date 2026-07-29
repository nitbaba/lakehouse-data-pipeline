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
