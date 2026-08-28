"""
Loads the already-extracted raw CSV (data/raw/clinical_trials_raw.csv, produced by
extract_api_data.py) into BigQuery, as the `raw.raw_clinical_trials` table dbt's
`stg_clinical_trials` source expects.

This is a one-off/occasional step, run manually after extract_api_data.py, not part
of the dbt DAG. extract_api_data.py itself is unchanged: it still writes locally
(CSV + the DuckDB dev warehouse) regardless of which dbt target you end up building.

Required environment variables (same ones documented in the README for the
`bigquery` dbt target):
    BIGQUERY_PROJECT   GCP project ID
    BIGQUERY_KEYFILE   path to a service account JSON key with BigQuery Data Editor
                       + BigQuery Job User on that project
Optional:
    BIGQUERY_DATASET   dataset dbt models are built into (default: main) - this
                       script creates it (empty) so dbt's first run has somewhere
                       to land; it does not load any data into it itself.
    RAW_DATASET        dataset for the raw source table (default: raw)
    BIGQUERY_LOCATION  dataset location (default: US - must match profiles.yml)

Usage:
    export BIGQUERY_PROJECT=your-project-id
    export BIGQUERY_KEYFILE=/path/to/key.json
    python src/load_raw_to_bigquery.py
"""
import logging
import os
import sys
from pathlib import Path

from google.cloud import bigquery
from google.oauth2 import service_account

logger = logging.getLogger(__name__)

RAW_CSV = Path("data/raw/clinical_trials_raw.csv")

# Mirrors the column types DuckDB's read_csv_auto already inferred for the same
# file (dev warehouse), so stg_clinical_trials's casting logic behaves identically
# on both backends.
SCHEMA = [
    bigquery.SchemaField("nct_id", "STRING"),
    bigquery.SchemaField("org_study_id", "STRING"),
    bigquery.SchemaField("brief_title", "STRING"),
    bigquery.SchemaField("official_title", "STRING"),
    bigquery.SchemaField("overall_status", "STRING"),
    bigquery.SchemaField("start_date", "STRING"),
    bigquery.SchemaField("start_date_type", "STRING"),
    bigquery.SchemaField("primary_completion_date", "STRING"),
    bigquery.SchemaField("primary_completion_date_type", "STRING"),
    bigquery.SchemaField("completion_date", "STRING"),
    bigquery.SchemaField("completion_date_type", "STRING"),
    bigquery.SchemaField("study_first_posted_date", "DATE"),
    bigquery.SchemaField("study_type", "STRING"),
    bigquery.SchemaField("phases", "STRING"),
    bigquery.SchemaField("primary_purpose", "STRING"),
    bigquery.SchemaField("enrollment_count", "INT64"),
    bigquery.SchemaField("enrollment_type", "STRING"),
    bigquery.SchemaField("lead_sponsor_name", "STRING"),
    bigquery.SchemaField("lead_sponsor_class", "STRING"),
    bigquery.SchemaField("conditions", "STRING"),
    bigquery.SchemaField("keywords", "STRING"),
    bigquery.SchemaField("brief_summary", "STRING"),
    bigquery.SchemaField("is_fda_regulated_drug", "BOOL"),
    bigquery.SchemaField("is_fda_regulated_device", "BOOL"),
    bigquery.SchemaField("locations_count", "INT64"),
    bigquery.SchemaField("countries", "STRING"),
    bigquery.SchemaField("intervention_types", "STRING"),
    bigquery.SchemaField("disposition_events", "STRING"),
]


def require_env(name):
    value = os.environ.get(name)
    if not value:
        sys.exit(f"Missing required environment variable: {name}")
    return value


def ensure_dataset(client, dataset_id, location):
    ref = bigquery.DatasetReference(client.project, dataset_id)
    try:
        client.get_dataset(ref)
        logger.info("Dataset %s already exists.", dataset_id)
    except Exception:
        ds = bigquery.Dataset(ref)
        ds.location = location
        client.create_dataset(ds)
        logger.info("Created dataset %s in %s.", dataset_id, location)


def main():
    project = require_env("BIGQUERY_PROJECT")
    keyfile = require_env("BIGQUERY_KEYFILE")
    raw_dataset = os.environ.get("RAW_DATASET", "raw")
    main_dataset = os.environ.get("BIGQUERY_DATASET", "main")
    location = os.environ.get("BIGQUERY_LOCATION", "US")

    if not RAW_CSV.exists():
        sys.exit(f"{RAW_CSV} not found - run src/extract_api_data.py first.")

    credentials = service_account.Credentials.from_service_account_file(keyfile)
    client = bigquery.Client(project=project, credentials=credentials)

    ensure_dataset(client, raw_dataset, location)
    ensure_dataset(client, main_dataset, location)

    table_id = f"{project}.{raw_dataset}.raw_clinical_trials"
    job_config = bigquery.LoadJobConfig(
        schema=SCHEMA,
        source_format=bigquery.SourceFormat.CSV,
        skip_leading_rows=1,
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
        allow_quoted_newlines=True,
    )

    logger.info("Loading %s into %s ...", RAW_CSV, table_id)
    with open(RAW_CSV, "rb") as f:
        job = client.load_table_from_file(f, table_id, job_config=job_config)
    job.result()

    table = client.get_table(table_id)
    logger.info("Done: %d rows loaded into %s.", table.num_rows, table_id)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )
    try:
        main()
    except Exception:
        logger.exception("La carga en BigQuery fallo.")
        sys.exit(1)
