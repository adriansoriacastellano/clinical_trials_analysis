"""
Shared sidebar filters. Rendered once per page (Streamlit reruns the whole
script on every page load - there's no way around that), but backed by
st.session_state so a selection made on one page is still there when you
navigate to the next: this is what turns 3 separate static pages into one
dashboard that responds to "show me only Phase III, 2015-2020" everywhere.
"""

import streamlit as st

from data import get_filter_options

_DEFAULTS_SET = "filters_defaults_set"


def render_sidebar_filters():
    options = get_filter_options()

    if _DEFAULTS_SET not in st.session_state:
        st.session_state.year_range = (options["year_min"], options["year_max"])
        st.session_state.countries = []
        st.session_state.phases = []
        st.session_state.sponsor_classes = []
        st.session_state[_DEFAULTS_SET] = True

    with st.sidebar:
        st.header("Filters")
        st.caption("Applied live, across every page — not a client-side re-slice.")

        st.slider(
            "Trial start year", min_value=options["year_min"], max_value=options["year_max"],
            key="year_range",
        )
        st.multiselect(
            "Country", options=options["countries"], key="countries",
            placeholder="All countries",
        )
        st.multiselect(
            "Phase", options=options["phases"], key="phases",
            placeholder="All phases",
        )
        st.multiselect(
            "Sponsor class", options=options["sponsor_classes"], key="sponsor_classes",
            placeholder="All sponsor classes",
        )

        if st.button("Reset filters", use_container_width=True):
            st.session_state.year_range = (options["year_min"], options["year_max"])
            st.session_state.countries = []
            st.session_state.phases = []
            st.session_state.sponsor_classes = []
            st.rerun()

    return {
        "year_range": st.session_state.year_range,
        "countries": st.session_state.countries,
        "phases": st.session_state.phases,
        "sponsor_classes": st.session_state.sponsor_classes,
    }
