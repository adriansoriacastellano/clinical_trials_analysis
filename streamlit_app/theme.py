"""
Shared color palette, Plotly layout defaults, and light CSS for every page.

Palette: navy + mint, chosen to match the existing Power BI dashboard for visual
continuity across the portfolio. Validated as a categorical pair with the
dataviz-skill validator (OKLCH lightness band, chroma floor, CVD Delta E under
simulated deuteranopia/protanopia/tritanopia, normal-vision separation, contrast
vs. a light surface) - navy #215E92 and mint #1F9E82 clear every check with no
warnings on a light surface. The app is pinned to Streamlit's light theme
(.streamlit/config.toml) specifically so this pair's validated contrast holds -
the same two hex values were not re-validated against a dark surface.

Charts here almost never need more than these two hues: nearly every chart is
"completion rate vs. abandonment rate" *by* some category, so color encodes the
metric (2 series, navy/mint), not the category - the category sits on the axis
instead. The status-distribution and Cross-Factor Explorer charts intentionally
use a single-hue sequential ramp (NAVY_SEQUENTIAL) rather than inventing more
categorical colors, precisely because the pair above was only validated as a
2-slot categorical palette, not a wider one.
"""

import plotly.graph_objects as go
import streamlit as st

NAVY = "#215E92"
MINT = "#1F9E82"

# Light-to-dark steps of the same navy hue, for magnitude-only charts (a status
# breakdown, a top-N donut, a heatmap) where color encodes "how much", not
# "which series".
NAVY_SEQUENTIAL = ["#CDE0F0", "#9FC2DE", "#6FA3CB", "#3F84B8", "#215E92", "#164569"]
NAVY_COLORSCALE = [
    [0.0, "#F3F7FB"], [0.2, "#CDE0F0"], [0.4, "#9FC2DE"],
    [0.6, "#6FA3CB"], [0.8, "#3F84B8"], [1.0, "#164569"],
]

SURFACE = "#FCFCFB"
GRID = "#E1E0D9"
TEXT_PRIMARY = "#0B0B0B"
TEXT_MUTED = "#6B6A65"

FONT_FAMILY = "system-ui, -apple-system, 'Segoe UI', sans-serif"


def apply_custom_css():
    """A page's-worth of visual polish that Streamlit's defaults don't give you
    for free: tabular figures on metrics (so digits line up), a firmer metric
    label style, and card-style borders that read as "dashboard" rather than
    "default Streamlit app". Targets Streamlit's own documented data-testid
    hooks (stable across versions) rather than internal class names."""
    st.markdown(f"""
        <style>
        [data-testid="stMetric"] {{
            background: white;
            border: 1px solid {GRID};
            border-radius: 10px;
            padding: 14px 16px 10px 16px;
        }}
        [data-testid="stMetricValue"] {{
            font-variant-numeric: tabular-nums;
            color: {NAVY};
        }}
        [data-testid="stMetricLabel"] {{
            font-size: 0.80rem;
            text-transform: uppercase;
            letter-spacing: 0.04em;
            color: {TEXT_MUTED};
        }}
        h2, h3 {{
            color: {TEXT_PRIMARY};
        }}
        </style>
    """, unsafe_allow_html=True)


def page_header(title, subtitle, icon=""):
    """A banded header instead of a plain st.title — the one deliberately
    branded element on every page, in the same navy as the charts."""
    st.markdown(f"""
        <div style="
            background: linear-gradient(135deg, {NAVY} 0%, #163F63 100%);
            border-radius: 12px; padding: 22px 26px; margin-bottom: 20px;
        ">
            <div style="color: white; font-size: 1.6rem; font-weight: 700;">{icon} {title}</div>
            <div style="color: #CFE0EF; font-size: 0.95rem; margin-top: 4px;">{subtitle}</div>
        </div>
    """, unsafe_allow_html=True)


def apply_layout(fig, title=None, height=420, showlegend=True):
    """Applies one consistent look to every chart in the app: same font, same
    muted gridlines, same margins - so the dashboard reads as one system rather
    than a pile of default-themed Plotly charts."""
    layout_kwargs = dict(
        height=height,
        showlegend=showlegend,
        plot_bgcolor=SURFACE,
        paper_bgcolor=SURFACE,
        font=dict(family=FONT_FAMILY, color=TEXT_PRIMARY, size=13),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        margin=dict(l=10, r=50, t=60 if title else 30, b=10),
        hoverlabel=dict(bgcolor="white", font_size=12, font_family=FONT_FAMILY),
    )
    # The real bug wasn't title=None - it was passing `title_font=...` as its own
    # top-level kwarg. Plotly's underscore shorthand turns that into a bare
    # layout.title = {font: {...}} object with no `text` key, and this version
    # of Plotly.js renders a title object with a missing text as the literal
    # string "undefined" instead of rendering nothing. Folding font into the
    # same dict as text - and only ever setting `title` as one unit, only when
    # there's real text - means layout.title never exists half-populated.
    if title:
        layout_kwargs["title"] = dict(text=title, font=dict(size=16, color=TEXT_PRIMARY))
    fig.update_layout(**layout_kwargs)
    fig.update_xaxes(showgrid=False, linecolor=GRID, tickfont=dict(color=TEXT_MUTED))
    fig.update_yaxes(showgrid=True, gridcolor=GRID, tickfont=dict(color=TEXT_MUTED))
    return fig


def rate_comparison_bar(df, label_col, title=None, height=440):
    """The one chart shape almost every Factors page needs: completion rate vs.
    abandonment rate, grouped by some category. Color always encodes the metric
    (navy=completion, mint=abandonment) - never the category - so this scales to
    any number of categories on the x-axis without touching the palette."""
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df[label_col], y=df["completion_rate"], name="Completion rate",
        marker_color=NAVY,
        text=df["completion_rate"].map(lambda v: f"{v:.1f}%"), textposition="outside",
    ))
    fig.add_trace(go.Bar(
        x=df[label_col], y=df["abandonment_rate"], name="Abandonment rate",
        marker_color=MINT,
        text=df["abandonment_rate"].map(lambda v: f"{v:.1f}%"), textposition="outside",
    ))
    fig.update_layout(barmode="group")
    fig.update_yaxes(title="Rate (%)")
    apply_layout(fig, title=title, height=height)
    return fig


def heatmap_chart(pivot_df, colorbar_title="Completion rate (%)", height=460):
    """pivot_df: a DataFrame already shaped rows=dim_a, cols=dim_b, values=rate."""
    fig = go.Figure(go.Heatmap(
        z=pivot_df.values,
        x=pivot_df.columns.tolist(),
        y=pivot_df.index.tolist(),
        colorscale=NAVY_COLORSCALE,
        text=pivot_df.values,
        texttemplate="%{text:.0f}%",
        textfont=dict(size=12),
        colorbar=dict(title=colorbar_title, ticksuffix="%"),
        xgap=3, ygap=3,
    ))
    apply_layout(fig, showlegend=False, height=height)
    fig.update_xaxes(showgrid=False, side="bottom")
    fig.update_yaxes(showgrid=False, autorange="reversed")
    return fig
