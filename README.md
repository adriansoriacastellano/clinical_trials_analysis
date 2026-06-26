# Clinical Trials Analysis

**What determines whether a clinical trial completes or is abandoned?**

An end-to-end data analytics project exploring completion and abandonment patterns across 188,687 clinical trials registered in ClinicalTrials.gov (Phases I–IV, 2015–2024).

Built as a portfolio project to demonstrate a full analytics pipeline: API ingestion → data warehouse → dimensional modelling → interactive dashboard.

---

## Table of Contents

- [Business Context](#business-context)
- [Data & Methodology](#data--methodology)
- [Technical Architecture](#technical-architecture)
- [Key Findings](#key-findings)
- [Dashboard](#dashboard)
- [Known Limitations & Future Work](#known-limitations--future-work)
- [How to Reproduce](#how-to-reproduce)
- [Repository Structure](#repository-structure)

---

## Business Context

Clinical trial completion is one of the most resource-intensive problems in drug development. A trial that is abandoned after years of execution represents not only wasted investment but a delayed or missed treatment for patients. Understanding which factors — trial phase, sponsor type, therapeutic area, enrollment size, and geography — are associated with higher abandonment rates has direct implications for portfolio planning in pharma, biotech, and CROs.

**Central question:**
> Which factors — trial phase, sponsor type, therapeutic area, enrollment size, and country — determine whether a clinical trial registered in ClinicalTrials.gov reaches completion or is abandoned/suspended?

**Data source:** [ClinicalTrials.gov API v2](https://clinicaltrials.gov/data-api/api) (public, no authentication required)  
**Scope:** Phases I–IV · 2015–2024 · 188,687 trials

---

## Data & Methodology

### Analytical Definitions

Three custom flags were derived from ClinicalTrials.gov's official status vocabulary:

| Flag | Definition | Rationale |
|---|---|---|
| `is_completed` | `overall_status = 'Completed'` | Official ClinicalTrials.gov definition of a trial reaching its planned endpoint |
| `is_abandoned` | `Terminated` OR `Withdrawn` OR `Suspended` | Trials that ended without reaching their planned endpoint — an analytical decision reflecting trials with no planned outcome |
| `is_concluded` | `is_completed OR is_abandoned` | Trials with a definitive outcome, used as the denominator for the temporal analysis |

### Temporal Bias — Maturity Effect

A raw completion rate chart shows a drop from ~82% (2015) to ~78% (2024). This is **not a real deterioration** — it is a maturity effect: trials registered in 2023–2024 have not had enough time to complete. They remain in active or recruiting status, pulling down the raw rate artificially.

To correct for this, the temporal analysis uses **Completion Rate (Concluded)** = Completed ÷ (Completed + Abandoned), which removes all still-active trials from the denominator. The corrected rate oscillates between 70–85% across the entire period with no meaningful downward trend, confirming that the apparent decline is a statistical artefact, not a real signal.

Both metrics are visible in the dashboard: the raw rate (55.9%) as a global KPI reflecting the full dataset as extracted, and the corrected rate (80.5%) for the temporal trend line.

### Enrollment Bands

Enrollment was categorised into six bands to enable comparison across trial sizes:

`<50` · `50–99` · `100–199` · `200–499` · `500–999` · `1,000+`

### Thresholds for Statistical Representativeness

Rates computed from very small sample sizes are not reliable. The following minimum thresholds were applied:

- Therapeutic areas: ≥ 1,500 trials
- Country bar chart: ≥ 15,000 trials
- Country scatter: ≥ 1,000 trials

---

## Technical Architecture

```
ClinicalTrials.gov API v2
         │
         ▼
  Python (extract_api_data.py)
  ├── Incremental saving every 3 pages
  ├── Checkpoint/resume logic (WSL2 stability)
  └── 188,687 records → raw JSON
         │
         ▼
  DuckDB (dwh_dev.duckdb)
  └── raw.raw_clinical_trials (28 columns)
         │
         ▼
  dbt Core (12 models · 21/21 tests PASS)
  ├── Staging: stg_clinical_trials (view)
  ├── Fact:    fct_clinical_trials (188,687 rows)
  ├── Dims:    dim_date · dim_status · dim_phase
  │            dim_sponsor · dim_condition · dim_country
  └── Bridges: brg_trial_phase · brg_trial_condition · brg_trial_country
         │
         ▼
  Parquet export (Python/DuckDB → Windows filesystem)
         │
         ▼
  Power BI Desktop
  ├── Semantic model (10 active relationships)
  ├── 15 DAX measures
  └── 3-page interactive dashboard

> **EDA:** Before building the dashboard, a full exploratory analysis was conducted in `notebooks/01_exploration_SLA.ipynb`. The notebook is executed with all outputs included and documents the analytical path from raw data to the five SLA questions answered.
```

**Stack:**

| Tool | Role |
|---|---|
| Python 3.12 | API ingestion, Parquet export |
| DuckDB | Local data warehouse |
| dbt Core | Transformations, data quality tests, lineage |
| Power BI Desktop | Dashboard and semantic model |
| Git + GitHub | Version control and public portfolio |

> **Note on Power BI connectivity:** Mart tables were exported to Parquet files on the Windows filesystem rather than connecting Power BI directly to the DuckDB database. The primary reason was file size: the full DuckDB file (`dwh_dev.duckdb`) weighs ~4 GB, while the exported Parquet files for the mart layer total a fraction of that. The DuckDB database remains the source of truth; the Parquet files are a lightweight transport layer for the reporting tier.

---

## Key Findings

### Global KPIs

| Metric | Value |
|---|---|
| Total trials | 188,687 |
| Completion Rate | 55.9% |
| Abandonment Rate | 13.5% |
| Completion Rate (Concluded) | 80.5% |
| Avg. enrollment | 344 participants |
| Avg. duration (completed trials) | 1,048 days (~2.9 years) |

---

### Finding 1 — Phase II is the riskiest phase

Phase II has the highest abandonment rate (15.5%) and the lowest completion rate (50.4%) of all phases. Phase III and Phase IV both achieve ~60% completion. This aligns with the known "Phase II valley of death" in drug development: early signals of safety (Phase I) are promising, but efficacy proof is where most programmes fail.

| Phase | Completion Rate | Abandonment Rate |
|---|---|---|
| Phase I | 53.6% | 14.5% |
| Phase II | 50.4% | 15.5% |
| Phase III | 60.2% | 11.5% |
| Phase IV | 59.2% | 11.5% |

---

### Finding 2 — NIH outperforms Industry in completion rate

The NIH leads all sponsor types with a 68.8% completion rate, higher than Industry (64.3%). This is counterintuitive — one might expect industry sponsors, with commercial pressure and tighter programme governance, to have higher completion rates. A plausible explanation is survivorship bias: NIH-funded trials may be smaller and more focused, whereas industry portfolios include a larger proportion of exploratory Phase II programmes that are designed to be stopped early if efficacy signals are weak.

---

### Finding 3 — Small trials fail disproportionately

Trials with fewer than 50 participants have a ~25% abandonment rate — five times higher than large trials (≥1,000 participants, ~5%). The relationship is monotonic: completion rate increases consistently with enrollment band. This likely reflects both resource constraints (underfunded small trials) and statistical design issues (insufficient power to detect effects, leading to early termination).

---

### Finding 4 — China is a geographic outlier

China has a 30.2% raw completion rate — among the lowest of major trial countries. However, its abandonment rate is only 4.6%. The gap is explained by a high volume of trials in "Unknown" status, which are neither completed nor abandoned — they simply have no reported outcome. This is not evidence of trial failure; it reflects a data completeness issue in ClinicalTrials.gov reporting for Chinese trials. Germany leads in completion rate among major countries.

---

### Finding 5 — HIV and Asthma are high-completion areas; oncology shows more variation

Among therapeutic areas with ≥1,500 trials, HIV Infections and Asthma show the highest completion rates (~80%). Cancer indications (Prostate Cancer, Breast Cancer) show considerably more abandonment (~15–20%), reflecting the complexity and duration of oncology programmes.

---

## Dashboard

### Overview

![Overview](assets/images/clinical_trials_analysis_overview.png)

The Overview page shows global KPIs, the corrected temporal trend (Completion Rate by Year using the Concluded denominator), and the distribution of all trials by status. The dual completion metrics — raw (55.9%) and concluded (80.5%) — are shown side by side to make the maturity effect immediately visible to any reader.

---

### Factors I: Phase, Sponsor & Enrollment

![Factors I](assets/images/clinical_trials_analysis_factors_i.png)

This page decomposes completion and abandonment rates by the three structural factors: trial phase, sponsor type, and enrollment size. Each chart shows both rates simultaneously to allow relative comparison.

---

### Factors II: Therapeutic Area & Country

![Factors II](assets/images/clinical_trials_analysis_factors_ii.png)

This page covers therapeutic areas (filtered to conditions with ≥1,500 trials, excluding healthy volunteer studies) and geography. The donut chart highlights the geographic concentration of global clinical research: the United States accounts for 53% of all trials in the dataset.

---

## Known Limitations & Future Work

### 1. Duplicate condition names in `dim_condition`

Free-text condition fields from the API contain orthographic variations: "COVID-19", "COVID", and "Covid19" are registered as separate conditions; "Crohn Disease" and "Crohn's Disease" similarly. This inflates the number of distinct conditions (~53,000) and may slightly alter rankings in the therapeutic area analysis.

**Proposed solution:** A dbt seed file with a normalisation dictionary mapping variant spellings to a canonical term. Not implemented in this version to keep the project scope contained.

### 2. `primary_purpose` field missing (API v2 migration)

The `primary_purpose` field (Treatment / Prevention / Diagnostic / etc.) is 100% null in the extracted data. This field was moved to a different location in ClinicalTrials.gov API v2 after the registry migration. It would be a valuable analytical dimension and is a candidate for a future extraction update.

### 3. `dim_intervention_type` not connected to the fact table

The intervention type dimension (Drug / Device / Biological / etc.) was built in dbt but has no bridge table connecting it to `fct_clinical_trials`, as trials can have multiple intervention types. The dimension was excluded from the Power BI model.

**Proposed solution:** Add `brg_trial_intervention` as a bridge table in dbt, re-export to Parquet, and add the corresponding visuals to the dashboard.

### 4. Parquet transport layer vs. direct ODBC connection

Mart tables are served to Power BI via Parquet export rather than a live DuckDB ODBC connection. This was a deliberate choice based on file size: the full DuckDB database is ~4 GB, making a direct connection less practical for a local development setup. In a production environment, the preferred architecture would be a cloud data warehouse (e.g. BigQuery, Snowflake) with a native Power BI connector and incremental refresh.

---

## How to Reproduce

### Requirements

- Python 3.12+
- dbt-duckdb
- DuckDB

```bash
# Clone the repository
git clone https://github.com/adriansoriacastellano/clinical_trials_analysis.git
cd clinical_trials_analysis

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt
```

### Step 1 — Extract data from the API

```bash
python src/extract_api_data.py
```

This script connects to the ClinicalTrials.gov API v2 (no authentication required), applies filters for Phases I–IV and the 2015–2024 registration window, and writes the results incrementally to `data/dwh_dev.duckdb`. The extraction runs for ~45–60 minutes and supports checkpointing: if interrupted, it can be resumed from the last saved page.

Expected output: **~188,687 trials** in `raw.raw_clinical_trials`.

### Step 2 — Run dbt transformations

```bash
cd dbt_project
dbt run
dbt test
```

Expected: 12 models built, **21/21 tests passing**.

### Step 3 — Export to Parquet and build the dashboard

The Power BI file (`.pbix`) is not included in this repository as it contains derived data. To rebuild the dashboard, first export the mart tables from DuckDB to Parquet:

```python
import duckdb

con = duckdb.connect("data/dwh_dev.duckdb")

tables = [
    "fct_clinical_trials",
    "dim_date", "dim_status", "dim_phase",
    "dim_sponsor", "dim_condition", "dim_country",
    "brg_trial_phase", "brg_trial_condition", "brg_trial_country"
]

for table in tables:
    con.execute(f"COPY marts.{table} TO 'exports/{table}.parquet' (FORMAT PARQUET)")

con.close()
```

Then in Power BI Desktop:
1. Get Data → Parquet → load each file from the `exports/` folder
2. Configure relationships as described in `docs/SLA.md`
3. Recreate the DAX measures listed in `docs/SLA.md`

---

## Repository Structure

```
clinical_trials_analysis/
├── dbt_project/
│   ├── models/
│   │   ├── staging/         # stg_clinical_trials
│   │   └── marts/           # fct + dims + bridges
│   ├── tests/
│   └── dbt_project.yml
├── src/
│   └── extract_api_data.py  # API ingestion script
├── notebooks/
│   └── 01_exploration_SLA.ipynb  # Full EDA: 5 analytical questions answered, 6 charts, executed with outputs
├── docs/
│   └── SLA.md               # Business requirements, KPI definitions, analytical questions
├── assets/
│   └── images/              # Dashboard screenshots
├── requirements.txt
├── Makefile
└── README.md
```

---

## Author

**Adrián Soria Castellano**  
Data Analytics · Analytics Engineering  
[GitHub](https://github.com/adriansoriacastellano)

*Background in Neuroscience (BSc + MSc). Transitioning into Data Analytics and Analytics Engineering. Currently building analytics engineering projects. Open to Data Analyst and Analytics Engineer roles.*
