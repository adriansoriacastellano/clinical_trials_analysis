"""
BigQuery access layer for the Streamlit dashboard. All pages import from here
rather than building their own client or writing raw SQL inline, so there is one
place that knows about credentials, table names, filtering, and caching.

Every query hits the `bigquery` dbt target's mart tables directly - the same
tables load_raw_to_bigquery.py + `dbt build -t bigquery` (manual, or via the
scheduled GitHub Actions workflow) keep populated. This app never talks to
DuckDB: it's read-only against whatever is currently live in BigQuery, which is
the point - see "A Live View: Streamlit + BigQuery" in the root README.

Every chart-facing query takes a `filters` dict (see filters.py) and applies it
as a real SQL WHERE clause via BigQuery query parameters - not a client-side
pandas filter - so filtering never has to pull more rows than it shows.
"""

import pandas as pd
import streamlit as st
from google.cloud import bigquery
from google.oauth2 import service_account

CACHE_TTL_SECONDS = 3600  # BigQuery only changes weekly; no need to re-query every view

DEFAULT_YEAR_RANGE = (2010, 2024)


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


def _to_bq_param(name, bq_type, value):
    if isinstance(value, tuple):
        return bigquery.ArrayQueryParameter(name, bq_type, list(value))
    return bigquery.ScalarQueryParameter(name, bq_type, value)


@st.cache_data(ttl=CACHE_TTL_SECONDS)
def run_query(sql, params=()):
    """`params` is a flat tuple of (name, bq_type, value) triples rather than real
    bigquery.QueryParameter objects, specifically so it stays hashable - that's
    what lets st.cache_data key on it (a distinct filter combination = a distinct
    cache entry, but the same combination reuses the cached result)."""
    query_params = [_to_bq_param(name, t, v) for name, t, v in params]
    job_config = bigquery.QueryJobConfig(query_parameters=query_params) if query_params else None
    return get_client().query(sql, job_config=job_config).to_dataframe()


# --- Shared filtering --------------------------------------------------

def _filter_conditions(filters):
    """Builds the WHERE clause + parameters every chart-facing query applies.
    Assumes the query's base table is `fct_clinical_trials` aliased `f`."""
    year_min, year_max = filters.get("year_range", DEFAULT_YEAR_RANGE)
    conditions = ["EXTRACT(YEAR FROM f.start_date) BETWEEN @year_min AND @year_max"]
    params = [("year_min", "INT64", year_min), ("year_max", "INT64", year_max)]

    if filters.get("sponsor_classes"):
        conditions.append(f"""f.sponsor_id IN (
            SELECT sponsor_id FROM {_table('dim_sponsor')}
            WHERE sponsor_class_label IN UNNEST(@sponsor_classes)
        )""")
        params.append(("sponsor_classes", "STRING", tuple(filters["sponsor_classes"])))

    if filters.get("countries"):
        conditions.append(f"""f.nct_id IN (
            SELECT nct_id FROM {_table('brg_trial_country')}
            WHERE country_name IN UNNEST(@countries)
        )""")
        params.append(("countries", "STRING", tuple(filters["countries"])))

    if filters.get("phases"):
        conditions.append(f"""f.nct_id IN (
            SELECT b.nct_id FROM {_table('brg_trial_phase')} b
            JOIN {_table('dim_phase')} p ON b.phase_id = p.phase_id
            WHERE p.phase_label IN UNNEST(@phases)
        )""")
        params.append(("phases", "STRING", tuple(filters["phases"])))

    return " AND ".join(conditions), tuple(params)


@st.cache_data(ttl=CACHE_TTL_SECONDS)
def get_filter_options():
    """Populates the sidebar widgets. Cached like everything else - the option
    lists themselves only change when the underlying data does."""
    sql = f"""
        SELECT
            (SELECT MIN(EXTRACT(YEAR FROM start_date)) FROM {_table('fct_clinical_trials')}) AS year_min,
            (SELECT MAX(EXTRACT(YEAR FROM start_date)) FROM {_table('fct_clinical_trials')}) AS year_max
    """
    years = run_query(sql).iloc[0]

    countries = run_query(f"""
        SELECT country_name, COUNT(*) AS n
        FROM {_table('brg_trial_country')}
        GROUP BY country_name ORDER BY n DESC LIMIT 15
    """)["country_name"].tolist()

    phases = run_query(f"""
        SELECT phase_label FROM {_table('dim_phase')}
        WHERE is_main_phase ORDER BY phase_id
    """)["phase_label"].tolist()

    sponsor_classes = run_query(f"""
        SELECT sponsor_class_label, SUM(1) AS n
        FROM {_table('fct_clinical_trials')} f
        JOIN {_table('dim_sponsor')} s ON f.sponsor_id = s.sponsor_id
        GROUP BY sponsor_class_label ORDER BY n DESC
    """)["sponsor_class_label"].tolist()

    return {
        "year_min": int(years.year_min), "year_max": int(years.year_max),
        "countries": countries, "phases": phases, "sponsor_classes": sponsor_classes,
    }


# --- Overview -----------------------------------------------------------

def get_global_kpis(filters):
    where_sql, params = _filter_conditions(filters)
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
        FROM {_table('fct_clinical_trials')} f
        WHERE {where_sql}
    """
    df = run_query(sql, params)
    return df.iloc[0] if len(df) else None


def get_completion_by_start_year(filters):
    """Completion rate among concluded trials, by the year each trial started -
    same 'Concluded' denominator and the same StartDate axis as the corrected
    trend in the Power BI Overview page (see Data & Methodology in the README
    for why Concluded, not all trials, is the right denominator here)."""
    where_sql, params = _filter_conditions(filters)
    sql = f"""
        SELECT
            EXTRACT(YEAR FROM start_date) AS start_year,
            COUNTIF(is_concluded) AS concluded_trials,
            ROUND(100 * SAFE_DIVIDE(COUNTIF(is_completed), COUNTIF(is_concluded)), 1)
                AS completion_rate
        FROM {_table('fct_clinical_trials')} f
        WHERE {where_sql}
        GROUP BY start_year
        HAVING concluded_trials >= 30
        ORDER BY start_year
    """
    return run_query(sql, params)


def get_status_distribution(filters):
    where_sql, params = _filter_conditions(filters)
    sql = f"""
        SELECT s.status_label, COUNT(*) AS n
        FROM {_table('fct_clinical_trials')} f
        JOIN {_table('dim_status')} s ON f.status_id = s.status_id
        WHERE {where_sql}
        GROUP BY s.status_label
        ORDER BY n DESC
    """
    return run_query(sql, params)


# --- Factors I: Phase, Intervention, Sponsor -----------------------------

def get_rates_by_phase(filters):
    where_sql, params = _filter_conditions(filters)
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
        WHERE p.is_main_phase AND {where_sql}
        GROUP BY p.phase_label, p.phase_id
        ORDER BY p.phase_id
    """
    return run_query(sql, params)


def get_rates_by_intervention(filters):
    where_sql, params = _filter_conditions(filters)
    sql = f"""
        SELECT
            INITCAP(REPLACE(i.intervention_name, '_', ' ')) AS intervention_name,
            COUNT(*) AS n,
            ROUND(100 * AVG(CAST(f.is_completed AS INT64)), 1) AS completion_rate,
            ROUND(100 * AVG(CAST(f.is_abandoned AS INT64)), 1) AS abandonment_rate
        FROM {_table('brg_trial_intervention')} b
        JOIN {_table('fct_clinical_trials')} f ON b.nct_id = f.nct_id
        JOIN {_table('dim_intervention_type')} i ON b.intervention_type_id = i.intervention_type_id
        WHERE {where_sql}
        GROUP BY i.intervention_name
        ORDER BY n DESC
    """
    return run_query(sql, params)


def get_rates_by_sponsor(filters):
    where_sql, params = _filter_conditions(filters)
    sql = f"""
        SELECT
            s.sponsor_class_label,
            COUNT(*) AS n,
            ROUND(100 * AVG(CAST(f.is_completed AS INT64)), 1) AS completion_rate,
            ROUND(100 * AVG(CAST(f.is_abandoned AS INT64)), 1) AS abandonment_rate
        FROM {_table('fct_clinical_trials')} f
        JOIN {_table('dim_sponsor')} s ON f.sponsor_id = s.sponsor_id
        WHERE {where_sql}
        GROUP BY s.sponsor_class_label
        ORDER BY n DESC
    """
    return run_query(sql, params)


# --- Factors II: Enrollment, Condition, Country ---------------------------

ENROLLMENT_BAND_ORDER = ["<50", "50-99", "100-199", "200-499", "500-999", "1,000+"]

_ENROLLMENT_BAND_CASE = """
    CASE
        WHEN enrollment_count < 50 THEN '<50'
        WHEN enrollment_count < 100 THEN '50-99'
        WHEN enrollment_count < 200 THEN '100-199'
        WHEN enrollment_count < 500 THEN '200-499'
        WHEN enrollment_count < 1000 THEN '500-999'
        ELSE '1,000+'
    END
"""


def get_rates_by_enrollment_band(filters):
    where_sql, params = _filter_conditions(filters)
    sql = f"""
        SELECT
            {_ENROLLMENT_BAND_CASE} AS enrollment_band,
            COUNT(*) AS n,
            ROUND(100 * AVG(CAST(is_completed AS INT64)), 1) AS completion_rate,
            ROUND(100 * AVG(CAST(is_abandoned AS INT64)), 1) AS abandonment_rate
        FROM {_table('fct_clinical_trials')} f
        WHERE enrollment_count IS NOT NULL AND {where_sql}
        GROUP BY enrollment_band
    """
    df = run_query(sql, params)
    df["enrollment_band"] = pd.Categorical(
        df["enrollment_band"], categories=ENROLLMENT_BAND_ORDER, ordered=True
    )
    return df.sort_values("enrollment_band")


def get_rates_by_condition(filters, min_trials=1000, top_n=10):
    """Matches Finding 5's methodology: conditions with >= min_trials, excluding
    non-medical 'healthy volunteer' studies via the same text filter used in the
    Power BI visual (see Known Limitations #3 in the README for why this is a
    text filter rather than a dimensional flag)."""
    where_sql, params = _filter_conditions(filters)
    sql = f"""
        SELECT
            b.condition_name,
            COUNT(*) AS n,
            ROUND(100 * AVG(CAST(f.is_completed AS INT64)), 1) AS completion_rate,
            ROUND(100 * AVG(CAST(f.is_abandoned AS INT64)), 1) AS abandonment_rate
        FROM {_table('brg_trial_condition')} b
        JOIN {_table('fct_clinical_trials')} f ON b.nct_id = f.nct_id
        WHERE LOWER(b.condition_name) NOT LIKE '%healthy%' AND {where_sql}
        GROUP BY b.condition_name
        HAVING n >= {min_trials}
        ORDER BY n DESC
        LIMIT {top_n}
    """
    return run_query(sql, params)


def get_rates_by_country(filters, top_n=4):
    where_sql, params = _filter_conditions(filters)
    sql = f"""
        SELECT
            b.country_name,
            COUNT(*) AS n,
            ROUND(100 * AVG(CAST(f.is_completed AS INT64)), 1) AS completion_rate,
            ROUND(100 * AVG(CAST(f.is_abandoned AS INT64)), 1) AS abandonment_rate
        FROM {_table('brg_trial_country')} b
        JOIN {_table('fct_clinical_trials')} f ON b.nct_id = f.nct_id
        WHERE {where_sql}
        GROUP BY b.country_name
        ORDER BY n DESC
        LIMIT {top_n}
    """
    return run_query(sql, params)


# --- Cross-Factor Explorer -----------------------------------------------
# Deliberately a small, curated set of dimensions - not every dimension in the
# star schema. Phase and Country go through a bridge table (a trial can carry
# more than one value), so crossing two bridged dimensions at once would
# double-fan-out the same trial; capping the choices here keeps every possible
# pairing legible instead of quietly multiplying trials into cells that don't
# add back up to the filtered total.

DIMENSIONS = {
    "Phase": {
        "value_expr": "p.phase_label",
        "join_sql": (
            f"JOIN {_table('brg_trial_phase')} b_phase ON f.nct_id = b_phase.nct_id "
            f"JOIN {_table('dim_phase')} p ON b_phase.phase_id = p.phase_id AND p.is_main_phase"
        ),
    },
    "Sponsor Class": {
        "value_expr": "s.sponsor_class_label",
        "join_sql": f"JOIN {_table('dim_sponsor')} s ON f.sponsor_id = s.sponsor_id",
    },
    "Enrollment Band": {
        "value_expr": _ENROLLMENT_BAND_CASE,
        "join_sql": "",
    },
    "Country (top 8)": {
        "value_expr": "c.country_name",
        "join_sql": (
            f"JOIN {_table('brg_trial_country')} b_country ON f.nct_id = b_country.nct_id "
            f"JOIN {_table('dim_country')} c ON b_country.country_id = c.country_id"
        ),
        # BigQuery doesn't allow an IN-subquery inside a JOIN...ON predicate, only
        # in WHERE - so the top-8 cap lives here instead of in join_sql above.
        "extra_where": (
            f"c.country_name IN ("
            f"  SELECT country_name FROM {_table('brg_trial_country')}"
            f"  GROUP BY country_name ORDER BY COUNT(*) DESC LIMIT 8"
            f")"
        ),
    },
}


def get_crosstab(dim_a, dim_b, filters, min_n=20):
    a, b = DIMENSIONS[dim_a], DIMENSIONS[dim_b]
    where_sql, params = _filter_conditions(filters)
    extra_where = " AND ".join(
        d["extra_where"] for d in (a, b) if d.get("extra_where")
    )
    if extra_where:
        where_sql = f"{where_sql} AND {extra_where}"
    sql = f"""
        SELECT
            {a['value_expr']} AS dim_a,
            {b['value_expr']} AS dim_b,
            COUNT(*) AS n,
            ROUND(100 * AVG(CAST(f.is_completed AS INT64)), 1) AS completion_rate
        FROM {_table('fct_clinical_trials')} f
        {a['join_sql']}
        {b['join_sql']}
        WHERE {where_sql}
        GROUP BY dim_a, dim_b
        HAVING n >= {min_n}
    """
    return run_query(sql, params)
