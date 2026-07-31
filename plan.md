# Open-Source Lakehouse Data Engineering Pipeline (`plan.md`)

## 1. Environment & Host Context
* **Host OS / Subsystem:** Windows Subsystem for Linux 2 (WSL2)
* **Linux Distribution:** Ubuntu 24.04.4 LTS
* **Execution Boundary:** All CLI tools, Docker engines, Python virtual environments, and Git operations execute natively inside the WSL2 Ubuntu environment (`/home/<user>/...` filesystem path for optimal I/O performance).

---

## 2. Project Overview & Objective
Build an end-to-end, production-grade, code-first Data Lakehouse using **dlt**, **Apache Iceberg**, **AWS S3 / Local MinIO**, **PySpark (Databricks / Local Spark)**, **Apache Airflow**, and **Metabase / Superset**, fully governed with **Terraform**, **Docker**, **Great Expectations**, and **GitHub Actions CI/CD**.

This project strictly adheres to enterprise engineering standards to serve as a portfolio centerpiece for Data Engineering roles.

---

## 3. Tech Stack Architecture & Learning Objectives

| Layer | Technology | Teaching Focus / Core Concept |
| :--- | :--- | :--- |
| **Cloud / Infra** | Terraform + AWS S3 (or MinIO) | Infrastructure as Code (IaC), IAM roles, object storage bucket policies. |
| **Storage Engine** | Apache Iceberg | Table format, ACID transactions on object storage, time travel, schema evolution. |
| **Ingestion** | dlt (data load tool) | Python-native API extraction, schema inference, schema evolution handling, state tracking. |
| **Processing** | PySpark (Dockerized / Databricks) | Distributed compute, DataFrame optimizations, Iceberg catalog management. |
| **Orchestration** | Apache Airflow | Dynamic DAG creation, custom hooks/operators, task dependencies, SLA alerts. |
| **Quality / Ops** | Great Expectations / pytest | Data validation at boundary points, automated schema and quality assertions. |
| **CI/CD** | GitHub Actions | Automated linting (`ruff`), unit testing, terraform validation, integration testing. |
| **Visualization** | Metabase / Superset | Connecting to Iceberg catalogs via query engines (Trino/DuckDB/Spark SQL). |

---

## 4. Working Rules & Execution Framework

1. **Teach-as-We-Build:** Every phase introduces the theoretical mechanism before code implementation (e.g., *how Iceberg metadata manifests work on disk*).
2. **Error Recovery Loop:** If a command or build step fails:
   * Stop immediately.
   * Provide the log/error output.
   * The issue will be diagnosed and fixed before moving to the next step.
3. **Opinionated Production Defaults:** Minimal choices will be requested from you. Implementations will default to industry best practices (e.g., strictly typed configurations, pre-commit hooks, modular DAGs, environment separation).
4. **Git-Aware State:** Work will proceed in structured branch workflows (`main`, `feature/*`). State checking will occur at every major checkpoint before merging.
5. **Portfolio Readiness:** Code must be fully modular, typed (`mypy`), formatted (`ruff`), documented with architecture diagrams, and fully reproducible via a single `make` or `docker-compose` command inside WSL2.

---

## 5. Master Implementation Roadmap

### Phase 1: WSL2 Environment Setup & Local Infrastructure
* [x] Verify Ubuntu 24.04.4 LTS setup: systemd activation, Python 3.12+ virtual environments, Docker integration, and `wsl.conf` settings.
* [x] Initialize Git repo, `.gitignore`, pre-commit hooks (`ruff`, `mypy`), and modular directory structure in `/home/`.
* [x] Configure Terraform scripts for S3 buckets / MinIO and IAM policies.
* [x] Set up local multi-container development environment via `docker-compose` (Spark, Iceberg REST catalog, Airflow, Postgres metadata store).

### Phase 2: Ingestion Layer (`dlt`)
* [x] Learn `dlt` core primitives: sources, resources, destinations, and pipeline state.
* [x] Build a custom `dlt` pipeline ingesting raw API data into object storage landing zones.
* [x] Add automated error handling and schema drift handling in `dlt`.

### Phase 3: Storage & Processing Layer (Apache Iceberg + PySpark)
* [x] Learn Apache Iceberg internals: Metadata JSON, Manifest Lists, and Manifest Files.
* [x] Configure PySpark with Iceberg REST catalog extensions.
* [x] Build PySpark Lakehouse transformations using the Medallion Architecture (Bronze -> Silver -> Gold).
* [x] Implement Iceberg Maintenance operations (Compaction, Snapshot Expiration).

### Phase 4: Data Quality & Testing Framework
* [x] Integrate **Great Expectations** / **dlt** validation rules at landing and Silver layers.
* [x] Write `pytest` test suites for PySpark transformations using local PySpark fixtures.

### Phase 5: Production Orchestration (Apache Airflow)
* [x] Design modular Airflow DAGs with custom DockerOperators / TaskFlow API.
* [x] Implement task retries, SLA monitoring, and dataset/asset triggers.
* [x] Enforce secrets management and environment variables via Airflow Connections.

### Phase 6: Enterprise CI/CD Pipeline (GitHub Actions)
* [x] Write GitHub Actions workflows for:
  * `lint-and-test.yml` (Ruff, Mypy, Pytest).
  * `terraform-ci.yml` (Terraform fmt, validate, plan).
  * `docker-build.yml` (Container build and scan).

### Phase 7: Analytics & Visualization Layer
* [x] Connect Metabase or Apache Superset to the Gold Iceberg tables.
* [x] Build production-ready executive dashboard and metrics reporting layer.

### Phase 8: Documentation & Portfolio Polish
* [x] Draft architectural documentation with lineage flow.
* [x] Write a clean, employer-ready `README.md` with step-by-step reproduction instructions.

### Phase 9: Beyond the Original Roadmap
Work added after the initial 8-phase roadmap was completed, in response to follow-up requests rather than the original plan:
* [x] Added Philadelphia as a fourth ingested location (`src/lakehouse/ingestion/open_meteo.py`, `src/lakehouse/quality/expectations.py`) — no changes needed anywhere downstream (Bronze/Silver/Gold, Trino, Superset), since the pipeline was already location-agnostic past ingestion.
* [x] Added [dbt](https://www.getdbt.com/) (via [dbt-trino](https://github.com/starburstdata/dbt-trino)) as a second, parallel Silver/Gold transformation path off the same Bronze table (`dbt/`), alongside the original PySpark path — not a replacement. Cross-checked row-for-row against the PySpark output for parity. Runs from an isolated venv in the Airflow image and as a sibling task (`dbt_transform`) in `processing_dag`.
* [x] Built a second Superset dashboard ("dbt Transformation Layer") reading from the dbt-produced tables, alongside the original dashboard built on the PySpark tables.
