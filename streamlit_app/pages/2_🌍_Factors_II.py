"""Factors II: Enrollment, Condition & Country — mirrors the third page of the
Power BI dashboard."""

import plotly.graph_objects as go
import streamlit as st

from data import get_rates_by_condition, get_rates_by_country, get_rates_by_enrollment_band
from theme import NAVY_SEQUENTIAL, apply_layout, rate_comparison_bar

st.set_page_config(page_title="Factors II · Clinical Trials Analysis", page_icon="🌍", layout="wide")

st.title("🌍 Factors II: Enrollment, Condition & Country")
st.caption(
    "Trial size, therapeutic area, and geography — the three factors least tied to "
    "how a trial is designed, and most tied to who it enrolls and where."
)

st.subheader("By Enrollment Band")
df_enrollment = get_rates_by_enrollment_band()
st.plotly_chart(rate_comparison_bar(df_enrollment, "enrollment_band"), use_container_width=True)
st.caption(
    "Bands with fewer than 50 participants abandon at a sharply higher rate than "
    "every other band — see Finding 3 in the README."
)

st.subheader("By Therapeutic Area")
st.caption("Conditions with ≥1,000 trials, excluding non-medical 'healthy volunteer' studies.")
df_condition = get_rates_by_condition()
st.plotly_chart(rate_comparison_bar(df_condition, "condition_name"), use_container_width=True)

st.subheader("By Country")
df_country = get_rates_by_country(top_n=4)
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
