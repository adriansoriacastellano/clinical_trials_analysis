"""
Shared sidebar filters. Rendered once per page (Streamlit reruns the whole
script on every page load - there's no way around that), but backed by
st.session_state so a selection made on one page is still there when you
navigate to the next: this is what turns 3 separate static pages into one
dashboard that responds to "show me only Phase III, 2015-2020" everywhere.

Deliberately does NOT bind widgets to session_state via `key=` alone: across a
multipage app, a widget re-instantiated on a different page under the same key
can have its stored value coerced to the widget's own default type on first
render there (a range slider's tuple silently becoming a bare int), which is
exactly the TypeError this shipped with initially. Instead, every widget reads
its current value explicitly via `value=` and its return value is written back
to session_state right after - one clear direction of data flow, no reliance
on Streamlit's key-matching across separate widget instances.
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

        year_range = st.slider(
            "Trial start year", min_value=options["year_min"], max_value=options["year_max"],
            value=st.session_state.year_range,
        )
        countries = st.multiselect(
            "Country", options=options["countries"], default=st.session_state.countries,
            placeholder="All countries",
        )
        phases = st.multiselect(
            "Phase", options=options["phases"], default=st.session_state.phases,
            placeholder="All phases",
        )
        sponsor_classes = st.multiselect(
            "Sponsor class", options=options["sponsor_classes"], default=st.session_state.sponsor_classes,
            placeholder="All sponsor classes",
        )

        st.session_state.year_range = year_range
        st.session_state.countries = countries
        st.session_state.phases = phases
        st.session_state.sponsor_classes = sponsor_classes

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
