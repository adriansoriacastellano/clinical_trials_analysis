import argparse
import csv
import json
import logging
import sys
import time
from pathlib import Path

import pandas as pd
import requests

BASE_URL = "https://clinicaltrials.gov/api/v2/studies"
PAGE_SIZE = 1000
CHECKPOINT_EVERY = 3
MAX_RETRIES = 3
RETRY_BACKOFF_SECONDS = 5
OUTPUT_CSV = Path("data/raw/clinical_trials_raw.csv")
CHECKPOINT_FILE = Path("data/raw/checkpoint.json")
STATE_FILE = Path("data/raw/last_extraction_state.json")
DB_PATH = Path("data/dwh_dev.duckdb")

QUERY_PARAMS = {
    "format": "json",
    "pageSize": PAGE_SIZE,
    "query.term": (
        "AREA[StartDate]RANGE[01/01/2010, 12/31/2024] AND "
        "(AREA[Phase]PHASE1 OR AREA[Phase]PHASE2 OR AREA[Phase]PHASE3 OR AREA[Phase]PHASE4)"
    ),
    "countTotal": "true",
}

logger = logging.getLogger(__name__)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Extrae estudios de ClinicalTrials.gov API v2."
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help=(
            "Fuerza una extraccion completa (2010-2024, fases I-IV), ignorando "
            "el estado de la ultima extraccion incremental."
        ),
    )
    return parser.parse_args()


def save_checkpoint(next_page_token, page, total_processed, mode):
    CHECKPOINT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CHECKPOINT_FILE, "w") as f:
        json.dump({
            "mode": mode,
            "next_page_token": next_page_token,
            "page": page,
            "total_processed": total_processed,
        }, f)


def load_checkpoint():
    if CHECKPOINT_FILE.exists():
        with open(CHECKPOINT_FILE) as f:
            return json.load(f)
    return None


def load_state():
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            return json.load(f)
    return None


def save_state(last_update_post_date):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump({"last_update_post_date": last_update_post_date}, f)


def build_query_params(mode, since_date=None):
    """Full mode reuses the original 2010-2024/Phase I-IV filter unchanged, so a
    from-scratch extraction is always reproducible. Incremental mode adds a
    LastUpdatePostDate lower bound on top of it, so only studies that are new or
    were edited since the last successful run are fetched."""
    params = QUERY_PARAMS.copy()
    if mode == "incremental" and since_date:
        year, month, day = since_date.split("-")
        params["query.term"] = (
            f"{QUERY_PARAMS['query.term']} AND "
            f"AREA[LastUpdatePostDate]RANGE[{month}/{day}/{year}, MAX]"
        )
    return params


def fetch_page(params):
    last_exc = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = requests.get(BASE_URL, params=params, timeout=120)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as exc:
            last_exc = exc
            logger.warning(
                "Intento %d/%d fallido al consultar la API: %s", attempt, MAX_RETRIES, exc
            )
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_BACKOFF_SECONDS * attempt)
    raise RuntimeError(
        f"No se pudo obtener la pagina tras {MAX_RETRIES} intentos"
    ) from last_exc


def flatten_study(study):
    protocol = study.get("protocolSection", {})
    identification = protocol.get("identificationModule", {})
    status = protocol.get("statusModule", {})
    description = protocol.get("descriptionModule", {})
    design = protocol.get("designModule", {})
    sponsor = protocol.get("sponsorCollaboratorsModule", {})
    oversight = protocol.get("oversightModule", {})
    conditions = protocol.get("conditionsModule", {})

    enrollment = design.get("enrollmentInfo", {})
    phases = design.get("phases", [])
    primary_purpose = design.get("primaryPurpose", "")
    study_type = design.get("studyType", "")

    lead_sponsor = {}
    lead = sponsor.get("leadSponsor", {})
    if lead:
        lead_sponsor = {
            "lead_sponsor_name": lead.get("name", ""),
            "lead_sponsor_class": lead.get("class", ""),
        }

    start_date = status.get("startDateStruct", {})
    primary_completion = status.get("primaryCompletionDateStruct", {})
    completion = status.get("completionDateStruct", {})
    study_first_posted = status.get("studyFirstPostDateStruct", {})

    disposition_events = []
    for event in protocol.get("dispositionEventsModule", {}).get("dispositionEvents", []):
        disposition_events.append({
            "disposition_type_code": event.get("dispositionTypeCode", ""),
            "disposition_description": event.get("dispositionDescription", ""),
            "disposition_date": event.get("dispositionDate", ""),
        })

    return {
        "nct_id": identification.get("nctId", ""),
        "org_study_id": identification.get("orgStudyIdInfo", {}).get("id", ""),
        "brief_title": identification.get("briefTitle", ""),
        "official_title": identification.get("officialTitle", ""),
        "overall_status": status.get("overallStatus", ""),
        "start_date": start_date.get("date", ""),
        "start_date_type": start_date.get("type", ""),
        "primary_completion_date": primary_completion.get("date", ""),
        "primary_completion_date_type": primary_completion.get("type", ""),
        "completion_date": completion.get("date", ""),
        "completion_date_type": completion.get("type", ""),
        "study_first_posted_date": study_first_posted.get("date", ""),
        "study_type": study_type,
        "phases": "|".join(phases) if phases else "",
        "primary_purpose": primary_purpose,
        "enrollment_count": enrollment.get("count", None),
        "enrollment_type": enrollment.get("type", ""),
        "lead_sponsor_name": lead_sponsor.get("lead_sponsor_name", ""),
        "lead_sponsor_class": lead_sponsor.get("lead_sponsor_class", ""),
        "conditions": "|".join(conditions.get("conditions", [])),
        "keywords": "|".join(conditions.get("keywords", [])),
        "brief_summary": description.get("briefSummary", ""),
        "is_fda_regulated_drug": oversight.get("isFdaRegulatedDrug", False),
        "is_fda_regulated_device": oversight.get("isFdaRegulatedDevice", False),
        "locations_count": len(protocol.get("contactsLocationsModule", {}).get("locations", [])),
        "countries": [],
        "intervention_types": [],
        "disposition_events": json.dumps(disposition_events, ensure_ascii=False),
    }


def flatten_countries(study):
    locations = study.get("protocolSection", {}).get("contactsLocationsModule", {}).get("locations", [])
    seen = set()
    countries = []
    for loc in locations:
        country = loc.get("country", "")
        if country and country not in seen:
            seen.add(country)
            countries.append(country)
    return countries


def flatten_interventions(study):
    interventions = study.get("protocolSection", {}).get("armsInterventionsModule", {}).get("interventions", [])
    types = set()
    for intervention in interventions:
        itype = intervention.get("type", "")
        if itype:
            types.add(itype)
    return list(types)


def last_update_post_date(study):
    return (
        study.get("protocolSection", {})
        .get("statusModule", {})
        .get("lastUpdatePostDateStruct", {})
        .get("date")
    )


COLUMNS = [
    "nct_id", "org_study_id", "brief_title", "official_title", "overall_status",
    "start_date", "start_date_type", "primary_completion_date", "primary_completion_date_type",
    "completion_date", "completion_date_type", "study_first_posted_date", "study_type",
    "phases", "primary_purpose", "enrollment_count", "enrollment_type",
    "lead_sponsor_name", "lead_sponsor_class", "conditions", "keywords",
    "brief_summary", "is_fda_regulated_drug", "is_fda_regulated_device",
    "locations_count", "countries", "intervention_types", "disposition_events",
]


def safe_csv_value(val):
    if val is None:
        return ""
    s = str(val).replace('"', '""').replace("\n", " ").replace("\r", "")
    return f'"{s}"'


def append_rows_to_csv(rows, write_header):
    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_CSV, "a", encoding="utf-8") as f:
        if write_header:
            f.write(",".join(COLUMNS) + "\n")
        for row in rows:
            f.write(",".join(safe_csv_value(row.get(c)) for c in COLUMNS) + "\n")


def merge_into_csv(new_rows):
    """Upserts new_rows into the existing full CSV by nct_id (studies that already
    exist are replaced with their updated version; new nct_ids are appended). The
    CSV always ends up holding the full historical extract, so downstream steps
    (DuckDB load, load_raw_to_bigquery.py) don't need to know incremental extraction
    happened at all."""
    new_df = pd.DataFrame(new_rows, columns=COLUMNS) if new_rows else pd.DataFrame(columns=COLUMNS)
    if OUTPUT_CSV.exists():
        existing_df = pd.read_csv(OUTPUT_CSV, dtype=str, keep_default_na=False)
        existing_df = existing_df[~existing_df["nct_id"].isin(new_df["nct_id"])]
        combined = pd.concat([existing_df, new_df], ignore_index=True)
    else:
        combined = new_df
    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    combined.to_csv(OUTPUT_CSV, index=False, quoting=csv.QUOTE_ALL)
    return len(combined)


def main():
    args = parse_args()
    state = None if args.full else load_state()
    mode = "incremental" if state else "full"
    since_date = state["last_update_post_date"] if state else None

    logger.info(
        "Iniciando extraccion (%s) de ClinicalTrials.gov API v2 (2010-2024, fases I-IV)...",
        mode,
    )
    if mode == "incremental":
        logger.info("Filtrando por LastUpdatePostDate >= %s", since_date)

    checkpoint = load_checkpoint()
    if checkpoint and checkpoint.get("mode") == mode:
        next_page_token = checkpoint["next_page_token"]
        page = checkpoint["page"]
        total_processed = checkpoint["total_processed"]
        logger.info(
            "Reanudando checkpoint (%s): pagina %d, %d estudios ya procesados.",
            mode, page, total_processed,
        )
    else:
        if checkpoint:
            logger.warning(
                "Checkpoint encontrado de un modo distinto (%s); se descarta.",
                checkpoint.get("mode"),
            )
        next_page_token = None
        page = 0
        total_processed = 0
        if mode == "full" and OUTPUT_CSV.exists():
            OUTPUT_CSV.unlink()

    params_base = build_query_params(mode, since_date)
    total_count = None
    last_checkpoint_page = page
    max_last_update = since_date
    write_header = mode == "full" and not (checkpoint and checkpoint.get("mode") == mode)
    incremental_rows = [] if mode == "incremental" else None

    while True:
        params = params_base.copy()
        if next_page_token:
            params["pageToken"] = next_page_token

        data = fetch_page(params)

        if total_count is None:
            total_count = data.get("totalCount", 0)
            logger.info("Total de estudios a extraer: %d", total_count)

        page_studies = data.get("studies", [])
        page += 1

        rows = []
        for study in page_studies:
            flat = flatten_study(study)
            flat["countries"] = json.dumps(flatten_countries(study), ensure_ascii=False)
            flat["intervention_types"] = json.dumps(flatten_interventions(study), ensure_ascii=False)
            rows.append(flat)

            candidate = last_update_post_date(study)
            if candidate and (max_last_update is None or candidate > max_last_update):
                max_last_update = candidate

        if rows:
            if mode == "full":
                append_rows_to_csv(rows, write_header)
                write_header = False
            else:
                incremental_rows.extend(rows)
            total_processed += len(rows)

        next_page_token = data.get("nextPageToken")
        logger.info(
            "Pagina %d: %d extraidos | Procesados: %d | Total esperado: %s",
            page, len(page_studies), total_processed, total_count,
        )

        if page - last_checkpoint_page >= CHECKPOINT_EVERY or not next_page_token:
            save_checkpoint(next_page_token or "", page, total_processed, mode)
            last_checkpoint_page = page
            logger.info(
                "  -> Checkpoint guardado (pagina %d, token: %s)",
                page, str(next_page_token)[:30] if next_page_token else "FINAL",
            )

        if not next_page_token:
            break

        time.sleep(0.5)

    logger.info("Extraccion completada. Total procesado: %d estudios.", total_processed)

    if mode == "incremental":
        merged_count = merge_into_csv(incremental_rows)
        logger.info(
            "Merge incremental: %d estudios nuevos/actualizados. CSV con %d filas totales.",
            len(incremental_rows), merged_count,
        )

    if CHECKPOINT_FILE.exists():
        CHECKPOINT_FILE.unlink()
        logger.info("Checkpoint eliminado.")

    if max_last_update:
        save_state(max_last_update)
        logger.info(
            "Estado guardado: la proxima extraccion incremental partira de LastUpdatePostDate >= %s",
            max_last_update,
        )

    logger.info("Cargando datos en DuckDB desde %s...", OUTPUT_CSV)
    import duckdb
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(DB_PATH))
    con.execute("CREATE SCHEMA IF NOT EXISTS raw")
    con.execute(f"""
        CREATE OR REPLACE TABLE raw.raw_clinical_trials AS
        SELECT * FROM read_csv_auto('{OUTPUT_CSV}')
    """)
    con.close()
    logger.info("Carga en DuckDB completada exitosamente.")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )
    try:
        main()
    except Exception:
        logger.exception("La extraccion fallo.")
        sys.exit(1)
