"""Overview page - global KPIs, the completion-rate trend, and the status mix.

Companion to the Power BI dashboard described in the root README, reading live
from BigQuery instead of a static Parquet export - see "A Live View: Streamlit +
BigQuery" there for how this fits into the rest of the pipeline. Unlike the
Power BI screenshots in the README, every chart here responds live to the
filters in the sidebar.
"""

import plotly.graph_objects as go
import streamlit as st

from data import fetch_parallel, get_completion_by_start_year, get_global_kpis, get_status_distribution
from filters import render_sidebar_filters
from theme import MINT, NAVY, NAVY_SEQUENTIAL, apply_custom_css, apply_layout, page_header

st.set_page_config(page_title="Clinical Trials Analysis", page_icon="🧪", layout="wide")
apply_custom_css()

page_header(
    "Clinical Trials Analysis", icon="🧪",
    subtitle=(
        "Completion and abandonment patterns across ClinicalTrials.gov (Phases I–IV, 2010–2024) — "
        "live from BigQuery, refreshed weekly. Use the filters in the sidebar to explore."
    ),
)

try:
    filters = render_sidebar_filters()
    # The 3 queries below are independent - fired concurrently instead of one
    # at a time, since each is its own BigQuery round trip.
    results = fetch_parallel(
        kpis=lambda: get_global_kpis(filters),
        year=lambda: get_completion_by_start_year(filters),
        status=lambda: get_status_distribution(filters),
    )
    kpis = results["kpis"]
except Exception as exc:
    st.error(
        "Couldn't reach BigQuery. If you're running this locally, check "
        "`.streamlit/secrets.toml` — see `streamlit_app/README.md`."
    )
    st.exception(exc)
    st.stop()

if kpis is None:
    st.warning("No trials match the current filters — try widening them in the sidebar.")
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

# Stacked full-width, not side-by-side: the status chart's trial counts (up to
# 6 digits) get clipped against their bars in a narrower column - full width
# gives them room.

st.subheader("Completion Rate (Concluded) by Year")
df_year = results["year"]
if df_year.empty:
    st.info("No concluded trials with at least 30 trials in a year match the current filters.")
else:
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df_year["start_year"], y=df_year["completion_rate"],
        mode="lines+markers", name="Completion rate",
        line=dict(color=NAVY, width=3), marker=dict(size=7, color=NAVY),
    ))
    for ref in (70, 85):
        fig.add_hline(
            y=ref, line_dash="dash", line_color=MINT, opacity=0.7,
            annotation_text=f"{ref}%", annotation_position="right",
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

st.subheader("Trials by Status")
df_status = results["status"]
if df_status.empty:
    st.info("No trials match the current filters.")
else:
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

st.divider()
st.page_link("pages/3_🔀_Cross-Factor_Explorer.py",
              label="→ Try the Cross-Factor Explorer: pick any two factors and see how they interact",
              icon="🔀")
