import json
import time
import os
import requests
from pathlib import Path

BASE_URL = "https://clinicaltrials.gov/api/v2/studies"
PAGE_SIZE = 1000
CHECKPOINT_EVERY = 3
OUTPUT_CSV = Path("data/raw/clinical_trials_raw.csv")
CHECKPOINT_FILE = Path("data/raw/checkpoint.json")
DB_PATH = Path("data/dwh_dev.duckdb")

QUERY_PARAMS = {
    "format": "json",
    "pageSize": PAGE_SIZE,
    "query.term": (
        "AREA[StartDate]RANGE[01/01/2015, 12/31/2024] AND "
        "AREA[Phase]PHASE1 OR AREA[Phase]PHASE2 OR AREA[Phase]PHASE3 OR AREA[Phase]PHASE4"
    ),
    "countTotal": "true",
}

def save_checkpoint(next_page_token, page, total_processed):
    CHECKPOINT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CHECKPOINT_FILE, "w") as f:
        json.dump({
            "next_page_token": next_page_token,
            "page": page,
            "total_processed": total_processed,
        }, f)

def load_checkpoint():
    if CHECKPOINT_FILE.exists():
        with open(CHECKPOINT_FILE) as f:
            return json.load(f)
    return None

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

def main():
    print("Iniciando extraccion de ClinicalTrials.gov API v2 (2015-2024, fases I-IV)...")

    checkpoint = load_checkpoint()
    if checkpoint:
        next_page_token = checkpoint["next_page_token"]
        page = checkpoint["page"]
        total_processed = checkpoint["total_processed"]
        write_header = False
        print(f"Reanudando desde checkpoint: pagina {page}, {total_processed} estudios ya guardados.")
    else:
        next_page_token = None
        page = 0
        total_processed = 0
        write_header = True
        if OUTPUT_CSV.exists():
            OUTPUT_CSV.unlink()

    total_count = None
    last_checkpoint_page = page

    while True:
        params = QUERY_PARAMS.copy()
        if next_page_token:
            params["pageToken"] = next_page_token

        response = requests.get(BASE_URL, params=params, timeout=120)
        response.raise_for_status()
        data = response.json()

        if total_count is None:
            total_count = data.get("totalCount", 0)
            print(f"Total de estudios a extraer: {total_count}")

        page_studies = data.get("studies", [])
        page += 1

        rows = []
        for study in page_studies:
            flat = flatten_study(study)
            flat["countries"] = json.dumps(flatten_countries(study), ensure_ascii=False)
            flat["intervention_types"] = json.dumps(flatten_interventions(study), ensure_ascii=False)
            rows.append(flat)

        if rows:
            append_rows_to_csv(rows, write_header)
            write_header = False
            total_processed += len(rows)

        next_page_token = data.get("nextPageToken")
        print(f"Pagina {page}: {len(page_studies)} extraidos | Guardados: {total_processed} | Total esperado: {total_count}")

        if page - last_checkpoint_page >= CHECKPOINT_EVERY or not next_page_token:
            save_checkpoint(next_page_token or "", page, total_processed)
            last_checkpoint_page = page
            print(f"  -> Checkpoint guardado (pagina {page}, token: {str(next_page_token)[:30] if next_page_token else 'FINAL'})")

        if not next_page_token:
            break

        time.sleep(0.5)

    print(f"Extraccion completada. Total guardado en CSV: {total_processed} estudios.")

    if CHECKPOINT_FILE.exists():
        CHECKPOINT_FILE.unlink()
        print("Checkpoint eliminado.")

    print(f"Cargando datos en DuckDB desde {OUTPUT_CSV}...")
    import duckdb
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(DB_PATH))
    con.execute("CREATE SCHEMA IF NOT EXISTS raw")
    con.execute(f"""
        CREATE OR REPLACE TABLE raw.raw_clinical_trials AS
        SELECT * FROM read_csv_auto('{OUTPUT_CSV}')
    """)
    con.close()
    print("Carga en DuckDB completada exitosamente.")

if __name__ == "__main__":
    main()
