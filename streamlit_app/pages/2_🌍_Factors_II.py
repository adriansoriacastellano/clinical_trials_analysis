"""Factors II: Enrollment, Condition & Country — mirrors the third page of the
Power BI dashboard, but live and filterable."""

import plotly.graph_objects as go
import streamlit as st

from data import get_rates_by_condition, get_rates_by_country, get_rates_by_enrollment_band
from filters import render_sidebar_filters
from theme import NAVY_SEQUENTIAL, apply_custom_css, apply_layout, page_header, rate_comparison_bar

st.set_page_config(page_title="Factors II · Clinical Trials Analysis", page_icon="🌍", layout="wide")
apply_custom_css()

page_header(
    "Factors II: Enrollment, Condition & Country", icon="🌍",
    subtitle="Trial size, therapeutic area, and geography.",
)

filters = render_sidebar_filters()

st.subheader("By Enrollment Band")
df_enrollment = get_rates_by_enrollment_band(filters)
if df_enrollment.empty:
    st.info("No trials with a reported enrollment count match the current filters.")
else:
    st.plotly_chart(rate_comparison_bar(df_enrollment, "enrollment_band"), use_container_width=True)
    st.caption(
        "Bands with fewer than 50 participants abandon at a sharply higher rate than "
        "every other band — see Finding 3 in the README."
    )

st.subheader("By Therapeutic Area")
st.caption("Conditions with ≥1,000 trials, excluding non-medical 'healthy volunteer' studies.")
df_condition = get_rates_by_condition(filters)
if df_condition.empty:
    st.info("No condition clears the 1,000-trial threshold with the current filters.")
else:
    st.plotly_chart(rate_comparison_bar(df_condition, "condition_name"), use_container_width=True)

st.subheader("By Country")
df_country = get_rates_by_country(filters, top_n=4)
if df_country.empty:
    st.info("No trials match the current filters.")
else:
    col_donut, col_bar = st.columns([2, 3])
    with col_donut:
        colors = NAVY_SEQUENTIAL[:len(df_country)][::-1]
        fig_donut = go.Figure(go.Pie(
            labels=df_country["country_name"], values=df_country["n"],
            hole=0.55, marker=dict(colors=colors, line=dict(color="white", width=2)),
            textinfo="label+percent", textposition="outside",
        ))
        apply_layout(fig_donut, title="Trial Volume", showlegend=False, height=380)
        st.plotly_chart(fig_donut, use_container_width=True)
    with col_bar:
        fig_bar = rate_comparison_bar(df_country, "country_name",
                                       title="Completion & Abandonment", height=380)
        st.plotly_chart(fig_bar, use_container_width=True)

with st.expander("Show underlying numbers"):
    tab1, tab2, tab3 = st.tabs(["Enrollment Band", "Condition", "Country"])
    tab1.dataframe(df_enrollment[["enrollment_band", "n", "completion_rate", "abandonment_rate"]],
                    use_container_width=True, hide_index=True)
    tab2.dataframe(df_condition[["condition_name", "n", "completion_rate", "abandonment_rate"]],
                    use_container_width=True, hide_index=True)
    tab3.dataframe(df_country[["country_name", "n", "completion_rate", "abandonment_rate"]],
                    use_container_width=True, hide_index=True)
