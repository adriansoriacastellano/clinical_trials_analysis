.DEFAULT_GOAL := help

.PHONY: help venv install extract extract-full \
	dbt-seed dbt-run dbt-test dbt-build dbt-docs pipeline \
	bigquery-load dbt-build-bigquery pipeline-bigquery clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*## ' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*## "}; {printf "  \033[36m%-22s\033[0m %s\n", $$1, $$2}'

venv: ## Create a virtual environment in .venv (activate it yourself afterwards)
	python3 -m venv .venv
	@echo "Run 'source .venv/bin/activate' to use it."

install: ## Install Python dependencies (run inside an activated venv)
	pip install -r requirements.txt

extract: ## Run the extraction script (incremental if state exists, full on first run)
	python src/extract_api_data.py

extract-full: ## Force a full extraction, ignoring saved incremental state
	python src/extract_api_data.py --full

dbt-seed: ## Load dbt seeds against the local DuckDB (dev) target
	cd dbt_project && dbt seed

dbt-run: ## Run dbt models against the local DuckDB (dev) target
	cd dbt_project && dbt run

dbt-test: ## Run dbt tests against the local DuckDB (dev) target
	cd dbt_project && dbt test

dbt-build: ## Seed + run + test in one DAG-ordered pass (dev/DuckDB)
	cd dbt_project && dbt build

dbt-docs: ## Generate and serve the dbt docs site locally
	cd dbt_project && dbt docs generate && dbt docs serve

pipeline: extract dbt-build ## Full local pipeline: extract, then build+test with dbt (dev/DuckDB)

bigquery-load: ## Load the extracted CSV into BigQuery's raw dataset
	python src/load_raw_to_bigquery.py

dbt-build-bigquery: ## Seed + run + test against the bigquery target
	cd dbt_project && dbt build -t bigquery

pipeline-bigquery: extract bigquery-load dbt-build-bigquery ## Full pipeline against BigQuery (mirrors the scheduled GitHub Actions workflow)

clean: ## Remove dbt build artifacts and Python caches
	cd dbt_project && dbt clean
	find . -type d -name '__pycache__' -exec rm -rf {} +
