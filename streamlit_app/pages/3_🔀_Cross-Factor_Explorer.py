"""Cross-Factor Explorer — the one page with no equivalent in the Power BI
dashboard. The 3 static pages there each break outcomes down by one factor at
a time; this lets you pick any two and see how they interact, as a live
heatmap. Not a re-implementation of a fixed screenshot — this only exists
because the data is queried live."""

import streamlit as st

from data import DIMENSIONS, get_crosstab
from filters import render_sidebar_filters
from theme import apply_custom_css, heatmap_chart, page_header

st.set_page_config(page_title="Cross-Factor Explorer · Clinical Trials Analysis",
                    page_icon="🔀", layout="wide")
apply_custom_css()

page_header(
    "Cross-Factor Explorer", icon="🔀",
    subtitle=(
        "Pick any two factors and see completion rate across their intersection — "
        "a view no static screenshot of this dashboard can show."
    ),
)

filters = render_sidebar_filters()

dim_names = list(DIMENSIONS.keys())
col_a, col_b = st.columns(2)
dim_a = col_a.selectbox("Factor A (rows)", dim_names, index=0)
dim_b_options = [d for d in dim_names if d != dim_a]
dim_b = col_b.selectbox("Factor B (columns)", dim_b_options, index=0)

df = get_crosstab(dim_a, dim_b, filters)

if df.empty:
    st.warning(
        "No combination of these two factors has at least 20 trials under the current "
        "filters — try widening the filters or picking a different pair."
    )
else:
    pivot = df.pivot(index="dim_a", columns="dim_b", values="completion_rate")
    counts = df.pivot(index="dim_a", columns="dim_b", values="n")

    st.subheader(f"Completion Rate: {dim_a} × {dim_b}")
    st.plotly_chart(heatmap_chart(pivot), use_container_width=True)
    st.caption(
        "Each cell is the completion rate (%) among trials with both that row's and that "
        "column's value; cells below 20 trials are left blank rather than shown as an "
        "unreliable rate. A trial that carries more than one Phase or Country is counted "
        "once per combination it belongs to — the same multi-membership caveat documented "
        "for the notebook's chi-square tests in the README applies here."
    )

    with st.expander("Show underlying counts"):
        st.dataframe(counts, use_container_width=True)
