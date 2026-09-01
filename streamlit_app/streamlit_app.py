"""Overview page - global KPIs, the completion-rate trend, and the status mix.

Companion to the Power BI dashboard described in the root README, reading live
from BigQuery instead of a static Parquet export - see "A Live View: Streamlit +
BigQuery" there for how this fits into the rest of the pipeline.
"""

import plotly.graph_objects as go
import streamlit as st

from data import get_completion_by_start_year, get_global_kpis, get_status_distribution
from theme import MINT, NAVY, NAVY_SEQUENTIAL, apply_layout

st.set_page_config(
    page_title="Clinical Trials Analysis",
    page_icon="🧪",
    layout="wide",
)

st.title("🧪 Clinical Trials Analysis")
st.caption(
    "Completion and abandonment patterns across ClinicalTrials.gov (Phases I–IV, 2010–2024). "
    "Live view of the `bigquery` dbt target — refreshed weekly by "
    "[Automated Weekly Extraction](https://github.com/adriansoriacastellano/clinical_trials_analysis#automated-weekly-extraction)."
)

try:
    kpis = get_global_kpis()
except Exception as exc:
    st.error(
        "Couldn't reach BigQuery. If you're running this locally, check "
        "`.streamlit/secrets.toml` — see `streamlit_app/README.md`."
    )
    st.exception(exc)
    st.stop()

st.subheader("Global KPIs")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Trials", f"{kpis.total_trials:,}")
c2.metric("Completion Rate", f"{kpis.completion_rate}%")
c3.metric("Abandonment Rate", f"{kpis.abandonment_rate}%")
c4.metric("Avg. Enrollment", f"{kpis.avg_enrollment:,.0f}")

c5, c6, c7, _ = st.columns(4)
c5.metric("Completion Rate (Concluded)", f"{kpis.completion_rate_concluded}%")
c6.metric("Abandonment Rate (Concluded)", f"{kpis.abandonment_rate_concluded}%")
c7.metric("Avg. Duration (completed)", f"{kpis.avg_duration_completed:,.0f} days")

st.divider()

col_left, col_right = st.columns([3, 2])

with col_left:
    st.subheader("Completion Rate by Start Year (Concluded trials)")
    df_year = get_completion_by_start_year()
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df_year["start_year"], y=df_year["completion_rate"],
        mode="lines+markers", name="Completion rate",
        line=dict(color=NAVY, width=3), marker=dict(size=7, color=NAVY),
    ))
    for ref, label in [(70, "70% reference"), (85, "85% reference")]:
        fig.add_hline(
            y=ref, line_dash="dash", line_color=MINT, opacity=0.7,
            annotation_text=label, annotation_position="right",
        )
    fig.update_yaxes(title="Completion rate (%)", range=[0, 100])
    fig.update_xaxes(title="Trial start year", dtick=1)
    apply_layout(fig, showlegend=False)
    st.plotly_chart(fig, use_container_width=True)
    st.caption(
        "Years with fewer than 30 concluded trials are dropped — too little volume "
        "for the rate to be meaningful (the most recent 1-2 years in particular are "
        "still mostly in progress, not yet concluded one way or the other)."
    )

with col_right:
    st.subheader("Trials by Status")
    df_status = get_status_distribution()
    df_status = df_status.sort_values("n")
    n_bars = len(df_status)
    colors = [NAVY_SEQUENTIAL[min(i, len(NAVY_SEQUENTIAL) - 1)]
              for i in range(n_bars - 1, -1, -1)]
    fig2 = go.Figure(go.Bar(
        x=df_status["n"], y=df_status["status_label"], orientation="h",
        marker_color=colors,
        text=df_status["n"].map(lambda v: f"{v:,}"), textposition="outside",
    ))
    fig2.update_xaxes(title="Trials")
    apply_layout(fig2, showlegend=False, height=420)
    st.plotly_chart(fig2, use_container_width=True)
