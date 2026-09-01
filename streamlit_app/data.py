"""
BigQuery access layer for the Streamlit dashboard. All pages import from here
rather than building their own client or writing raw SQL inline, so there is one
place that knows about credentials, table names, and caching.

Every query hits the `bigquery` dbt target's mart tables directly - the same
tables load_raw_to_bigquery.py + `dbt build -t bigquery` (manual, or via the
scheduled GitHub Actions workflow) keep populated. This app never talks to
DuckDB: it's read-only against whatever is currently live in BigQuery, which is
the point - see "A Live View: Streamlit + BigQuery" in the root README.
"""

import pandas as pd
import streamlit as st
from google.cloud import bigquery
from google.oauth2 import service_account

CACHE_TTL_SECONDS = 3600  # BigQuery only changes weekly; no need to re-query every view


@st.cache_resource
def get_client():
    credentials = service_account.Credentials.from_service_account_info(
        dict(st.secrets["gcp_service_account"])
    )
    return bigquery.Client(project=st.secrets["bigquery"]["project"], credentials=credentials)


def _table(name):
    project = st.secrets["bigquery"]["project"]
    dataset = st.secrets["bigquery"].get("dataset", "main")
    return f"`{project}.{dataset}.{name}`"


@st.cache_data(ttl=CACHE_TTL_SECONDS)
def run_query(sql):
    return get_client().query(sql).to_dataframe()


# --- Overview -----------------------------------------------------------

def get_global_kpis():
    sql = f"""
        SELECT
            COUNT(*) AS total_trials,
            ROUND(100 * AVG(CAST(is_completed AS INT64)), 1) AS completion_rate,
            ROUND(100 * AVG(CAST(is_abandoned AS INT64)), 1) AS abandonment_rate,
            ROUND(100 * SAFE_DIVIDE(COUNTIF(is_completed), COUNTIF(is_concluded)), 1)
                AS completion_rate_concluded,
            ROUND(100 * SAFE_DIVIDE(COUNTIF(is_abandoned), COUNTIF(is_concluded)), 1)
                AS abandonment_rate_concluded,
            ROUND(AVG(enrollment_count), 0) AS avg_enrollment,
            ROUND(AVG(CASE WHEN is_completed THEN duration_days END), 0) AS avg_duration_completed
        FROM {_table('fct_clinical_trials')}
    """
    return run_query(sql).iloc[0]


def get_completion_by_start_year():
    """Completion rate among concluded trials, by the year each trial started -
    same 'Concluded' denominator and the same StartDate axis as the corrected
    trend in the Power BI Overview page (see Data & Methodology in the README
    for why Concluded, not all trials, is the right denominator here)."""
    sql = f"""
        SELECT
            EXTRACT(YEAR FROM start_date) AS start_year,
            COUNTIF(is_concluded) AS concluded_trials,
            ROUND(100 * SAFE_DIVIDE(COUNTIF(is_completed), COUNTIF(is_concluded)), 1)
                AS completion_rate
        FROM {_table('fct_clinical_trials')}
        WHERE start_date IS NOT NULL
        GROUP BY start_year
        HAVING concluded_trials >= 30
        ORDER BY start_year
    """
    return run_query(sql)


def get_status_distribution():
    sql = f"""
        SELECT s.status_label, COUNT(*) AS n
        FROM {_table('fct_clinical_trials')} f
        JOIN {_table('dim_status')} s ON f.status_id = s.status_id
        GROUP BY s.status_label
        ORDER BY n DESC
    """
    return run_query(sql)


# --- Factors I: Phase, Intervention, Sponsor -----------------------------

def get_rates_by_phase():
    sql = f"""
        SELECT
            p.phase_label,
            p.phase_id,
            COUNT(*) AS n,
            ROUND(100 * AVG(CAST(f.is_completed AS INT64)), 1) AS completion_rate,
            ROUND(100 * AVG(CAST(f.is_abandoned AS INT64)), 1) AS abandonment_rate
        FROM {_table('brg_trial_phase')} b
        JOIN {_table('fct_clinical_trials')} f ON b.nct_id = f.nct_id
        JOIN {_table('dim_phase')} p ON b.phase_id = p.phase_id
        WHERE p.is_main_phase
        GROUP BY p.phase_label, p.phase_id
        ORDER BY p.phase_id
    """
    return run_query(sql)


def get_rates_by_intervention():
    sql = f"""
        SELECT
            INITCAP(REPLACE(i.intervention_name, '_', ' ')) AS intervention_name,
            COUNT(*) AS n,
            ROUND(100 * AVG(CAST(f.is_completed AS INT64)), 1) AS completion_rate,
            ROUND(100 * AVG(CAST(f.is_abandoned AS INT64)), 1) AS abandonment_rate
        FROM {_table('brg_trial_intervention')} b
        JOIN {_table('fct_clinical_trials')} f ON b.nct_id = f.nct_id
        JOIN {_table('dim_intervention_type')} i ON b.intervention_type_id = i.intervention_type_id
        GROUP BY i.intervention_name
        ORDER BY n DESC
    """
    return run_query(sql)


def get_rates_by_sponsor():
    sql = f"""
        SELECT
            s.sponsor_class_label,
            COUNT(*) AS n,
            ROUND(100 * AVG(CAST(f.is_completed AS INT64)), 1) AS completion_rate,
            ROUND(100 * AVG(CAST(f.is_abandoned AS INT64)), 1) AS abandonment_rate
        FROM {_table('fct_clinical_trials')} f
        JOIN {_table('dim_sponsor')} s ON f.sponsor_id = s.sponsor_id
        GROUP BY s.sponsor_class_label
        ORDER BY n DESC
    """
    return run_query(sql)


# --- Factors II: Enrollment, Condition, Country ---------------------------

ENROLLMENT_BAND_ORDER = ["<50", "50-99", "100-199", "200-499", "500-999", "1,000+"]


def get_rates_by_enrollment_band():
    sql = f"""
        SELECT
            CASE
                WHEN enrollment_count < 50 THEN '<50'
                WHEN enrollment_count < 100 THEN '50-99'
                WHEN enrollment_count < 200 THEN '100-199'
                WHEN enrollment_count < 500 THEN '200-499'
                WHEN enrollment_count < 1000 THEN '500-999'
                ELSE '1,000+'
            END AS enrollment_band,
            COUNT(*) AS n,
            ROUND(100 * AVG(CAST(is_completed AS INT64)), 1) AS completion_rate,
            ROUND(100 * AVG(CAST(is_abandoned AS INT64)), 1) AS abandonment_rate
        FROM {_table('fct_clinical_trials')}
        WHERE enrollment_count IS NOT NULL
        GROUP BY enrollment_band
    """
    df = run_query(sql)
    df["enrollment_band"] = pd.Categorical(
        df["enrollment_band"], categories=ENROLLMENT_BAND_ORDER, ordered=True
    )
    return df.sort_values("enrollment_band")


def get_rates_by_condition(min_trials=1000, top_n=10):
    """Matches Finding 5's methodology: conditions with >= min_trials, excluding
    non-medical 'healthy volunteer' studies via the same text filter used in the
    Power BI visual (see Known Limitations #3 in the README for why this is a
    text filter rather than a dimensional flag)."""
    sql = f"""
        SELECT
            b.condition_name,
            COUNT(*) AS n,
            ROUND(100 * AVG(CAST(f.is_completed AS INT64)), 1) AS completion_rate,
            ROUND(100 * AVG(CAST(f.is_abandoned AS INT64)), 1) AS abandonment_rate
        FROM {_table('brg_trial_condition')} b
        JOIN {_table('fct_clinical_trials')} f ON b.nct_id = f.nct_id
        WHERE LOWER(b.condition_name) NOT LIKE '%healthy%'
        GROUP BY b.condition_name
        HAVING n >= {min_trials}
        ORDER BY n DESC
        LIMIT {top_n}
    """
    return run_query(sql)


def get_rates_by_country(top_n=4):
    sql = f"""
        SELECT
            b.country_name,
            COUNT(*) AS n,
            ROUND(100 * AVG(CAST(f.is_completed AS INT64)), 1) AS completion_rate,
            ROUND(100 * AVG(CAST(f.is_abandoned AS INT64)), 1) AS abandonment_rate
        FROM {_table('brg_trial_country')} b
        JOIN {_table('fct_clinical_trials')} f ON b.nct_id = f.nct_id
        GROUP BY b.country_name
        ORDER BY n DESC
        LIMIT {top_n}
    """
    return run_query(sql)
