.DEFAULT_GOAL := help
VENV := .venv
PY := $(VENV)/bin/python
PIP := $(VENV)/bin/pip

.PHONY: help
help: ## Show this help
	@grep -hE '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

.PHONY: init
init: $(VENV)/bin/activate .env terraform/terraform.tfvars ## Set up venv, deps, pre-commit, and local config
	$(PIP) install -e ".[dev]"
	$(VENV)/bin/pre-commit install

$(VENV)/bin/activate:
	python3 -m venv $(VENV)

.env:
	cp .env.example .env
	@fernet=$$(python3 -c "import base64, os; print(base64.urlsafe_b64encode(os.urandom(32)).decode())"); \
	secret=$$(python3 -c "import secrets; print(secrets.token_hex(32))"); \
	jupyter_token=$$(python3 -c "import secrets; print(secrets.token_hex(24))"); \
	sed -i "s|^AIRFLOW_FERNET_KEY=.*|AIRFLOW_FERNET_KEY=$$fernet|" .env; \
	sed -i "s|^AIRFLOW_WEBSERVER_SECRET_KEY=.*|AIRFLOW_WEBSERVER_SECRET_KEY=$$secret|" .env; \
	sed -i "s|^JUPYTER_TOKEN=.*|JUPYTER_TOKEN=$$jupyter_token|" .env
	@echo "Created .env — fill in LAKEHOUSE_BUCKET_NAME after 'make tf-apply'."

terraform/terraform.tfvars:
	cp terraform/terraform.tfvars.example terraform/terraform.tfvars

.PHONY: fmt
fmt: ## Format Python and Terraform
	$(VENV)/bin/ruff format .
	terraform fmt -recursive terraform/

.PHONY: lint
lint: ## Lint Python and validate Terraform
	$(VENV)/bin/ruff check .
	$(VENV)/bin/mypy src tests
	terraform fmt -check -recursive terraform/
	terraform -chdir=terraform validate

.PHONY: precommit
precommit: ## Run all pre-commit hooks against all files
	$(VENV)/bin/pre-commit run --all-files

.PHONY: test
test: ## Run pytest
	$(VENV)/bin/pytest

.PHONY: ingest
ingest: ## Run the dlt ingestion pipeline against S3 (needs a filled-in .env)
	set -a && . ./.env && set +a && $(PY) -m lakehouse.ingestion.pipeline

.PHONY: tf-init
tf-init: ## terraform init
	terraform -chdir=terraform init

.PHONY: tf-plan
tf-plan: ## terraform plan
	terraform -chdir=terraform plan

.PHONY: tf-apply
tf-apply: ## terraform apply
	terraform -chdir=terraform apply

.PHONY: tf-destroy
tf-destroy: ## terraform destroy
	terraform -chdir=terraform destroy

.PHONY: tf-output
tf-output: ## Show terraform outputs
	terraform -chdir=terraform output

.PHONY: up
up: ## Start the local docker-compose stack
	docker compose up -d --build

.PHONY: down
down: ## Stop the local docker-compose stack
	docker compose down

.PHONY: down-v
down-v: ## Stop the stack and remove volumes
	docker compose down -v

.PHONY: logs
logs: ## Tail logs from all services
	docker compose logs -f

.PHONY: ps
ps: ## Show status of all services
	docker compose ps

.PHONY: clean
clean: ## Remove caches and build artifacts
	rm -rf .mypy_cache .ruff_cache .pytest_cache .coverage htmlcov build dist *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} +
