"""Factors I: Phase, Intervention Type & Sponsor — mirrors the second page of
the Power BI dashboard, but live and filterable."""

import streamlit as st

from data import fetch_parallel, get_rates_by_intervention, get_rates_by_phase, get_rates_by_sponsor
from filters import render_sidebar_filters
from theme import apply_custom_css, page_header, rate_comparison_bar

st.set_page_config(page_title="Factors I · Clinical Trials Analysis", page_icon="📊", layout="wide")
apply_custom_css()

page_header(
    "Factors I: Phase, Intervention & Sponsor", icon="📊",
    subtitle="How completion and abandonment vary by trial phase, intervention type, and sponsor class.",
)

filters = render_sidebar_filters()

# 3 independent queries, fired concurrently rather than one at a time.
results = fetch_parallel(
    phase=lambda: get_rates_by_phase(filters),
    intervention=lambda: get_rates_by_intervention(filters),
    sponsor=lambda: get_rates_by_sponsor(filters),
)
df_phase, df_intervention, df_sponsor = results["phase"], results["intervention"], results["sponsor"]

st.subheader("By Trial Phase")
st.plotly_chart(rate_comparison_bar(df_phase, "phase_label"), use_container_width=True)

st.subheader("By Intervention Type")
st.plotly_chart(rate_comparison_bar(df_intervention, "intervention_name"), use_container_width=True)

st.subheader("By Sponsor Class")
st.plotly_chart(rate_comparison_bar(df_sponsor, "sponsor_class_label"), use_container_width=True)

with st.expander("Show underlying numbers"):
    tab1, tab2, tab3 = st.tabs(["Phase", "Intervention Type", "Sponsor Class"])
    tab1.dataframe(df_phase[["phase_label", "n", "completion_rate", "abandonment_rate"]],
                    use_container_width=True, hide_index=True)
    tab2.dataframe(df_intervention[["intervention_name", "n", "completion_rate", "abandonment_rate"]],
                    use_container_width=True, hide_index=True)
    tab3.dataframe(df_sponsor[["sponsor_class_label", "n", "completion_rate", "abandonment_rate"]],
                    use_container_width=True, hide_index=True)
