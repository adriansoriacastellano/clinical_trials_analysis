# Requirements and Logical Architecture Document

## Section A — Business Requirements (to be completed in Phase 1)

* **Main Objective:** Identify which factors — trial phase, intervention type, sponsor type, therapeutic area, size, and country — determine whether a clinical trial registered in ClinicalTrials.gov reaches completion or is abandoned/suspended.

* **Data Source:** ClinicalTrials.gov public API v2. REST endpoint, no authentication. Base URL: `https://clinicaltrials.gov/api/v2/studies`. The initial ingestion covers the 2010-2024 period (refreshed weekly since — see the README's "Automated Weekly Extraction").

* **Granularity of the Final Model:** One clinical trial. Each row is a unique study identified by its NCT ID.

* **KPI Glossary:**
  * **Completion rate:** `COUNT(completed_trials) / COUNT(total_trials)`
  * **Abandonment rate:** `COUNT(terminated_trials + suspended_trials + withdrawn_trials) / COUNT(total_trials)`
  * **Average trial duration:** `AVG(actual_end_date - actual_start_date)` in days, for completed trials only
  * **Average trial size:** `AVG(enrollment_count)`
  * **Trial size bands (enrollment):** `<50` · `50-99` · `100-199` · `200-499` · `500-999` · `1000+` — used for the completion-rate-by-size analysis
  * **Completion rate by phase:** `COUNT(completed_phase_X) / COUNT(total_phase_X)` for phases I, II, III, IV
  * **Completion rate by sponsor type:** `COUNT(completed_sponsor_type) / COUNT(total_sponsor_type)` (Industry, Individual, Federal, NIH, Network, Other, Other Government)
  * **Completion rate by intervention type:** `COUNT(completed_intervention_type) / COUNT(total_intervention_type)` (Drug, Biological, Device, Behavioral, Dietary Supplement, Combination Product, Diagnostic Test, Procedure, Genetic, Radiation, Other)
  * **Completion rate by therapeutic area:** For the top 5 areas with the most trials (minimum threshold ≥1,000 trials, excluding non-medical conditions such as "healthy volunteer")
  * **Status distribution:** `COUNT` per `overall_status` (COMPLETED, TERMINATED, WITHDRAWN, SUSPENDED, etc.)

* **Update Frequency:** Originally a one-off historical analysis (single ingestion for 2010-2024, no periodic refresh required). It is now refreshed weekly by an automated incremental extraction — see the README's "Automated Weekly Extraction".

* **PII Fields Detected:** None. ClinicalTrials.gov is a public database of studies, not of patients. It contains no names, emails, or identifiable data about individuals.

## Section B — Technical Architecture (to be completed in Phase 3, before marts)

* **Raw Table Inspected:** `raw.raw_clinical_trials` — 137,556 rows, 28 columns. Source: ClinicalTrials.gov public API v2 (no authentication).

* **Raw Column Catalog:**
  | Column | Type | Content |
  |---|---|---|
  | `nct_id` | VARCHAR | Unique trial ID (PK) |
  | `overall_status` | VARCHAR | Current status (COMPLETED, TERMINATED, WITHDRAWN, SUSPENDED, RECRUITING...) |
  | `phases` | VARCHAR | Pipe-delimited phases (PHASE1\|PHASE2...) |
  | `lead_sponsor_class` | VARCHAR | Sponsor type (INDUSTRY, NIH, OTHER, OTHER_GOV...) |
  | `conditions` | VARCHAR | Pipe-delimited conditions/therapeutic areas |
  | `countries` | VARCHAR | JSON array of countries |
  | `enrollment_count` | BIGINT | Trial size (nulls present) |
  | `start_date` / `primary_completion_date` / `completion_date` | VARCHAR | Dates in mixed format (YYYY-MM-DD, YYYY-MM) |
  | `study_first_posted_date` | DATE | Date first posted on CT.gov |
  | `primary_purpose` | VARCHAR | 100% null (not available in API v2) |
  | `intervention_types` | VARCHAR | JSON array of intervention types |
  | `disposition_events` | VARCHAR | JSON array of disposition events |

* **Actual Marts Table Schema:**
  * **Fact table** (`fct_clinical_trials`): One row per clinical trial (NCT ID), with computed metrics and foreign keys to dimensions.
  * **Dimension tables:** `dim_date`, `dim_status`, `dim_phase`, `dim_sponsor`, `dim_condition` (with `condition_name_raw` and `condition_name_normalized` columns for traceability), `dim_country`, `dim_intervention_type`.
  * **Bridge tables (N:N):** `brg_trial_phase`, `brg_trial_condition`, `brg_trial_country`, `brg_trial_intervention` — required because a single trial can be associated with multiple phases, conditions, countries, and intervention types.
  * **Intermediate layer:** `int_condition_normalized` — normalizes orthographic variants of condition names via the `condition_normalization.csv` seed (3,771 raw → normalized mappings).

* **Tie-out Criterion:** The total trial count per `overall_status` in DuckDB must match exactly what is shown in Power BI.

* **PII Fields Confirmed:** None. Confirmed after inspecting the raw schema: ClinicalTrials.gov contains no patient data, only study metadata.

## Section C — Analytical Questions

1. What percentage of trials are completed vs. abandoned, and how has this evolved by year?
2. Which phases have the highest abandonment rate?
3. Do pharmaceutical industry trials complete more often than academic ones?
4. Which therapeutic areas concentrate the most abandonments?
5. Does trial size correlate with the probability of completion?
6. Which intervention types (drug, device, behavioral...) show the highest completion or abandonment rate?
