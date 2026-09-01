"""
Shared color palette and Plotly layout defaults for every page.

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
instead. The one chart that genuinely encodes a category by color (status
distribution) intentionally uses a single hue (see NAVY_SEQUENTIAL) rather than
inventing more categorical colors, precisely because the pair above was only
validated as a 2-slot palette.
"""

import plotly.graph_objects as go

NAVY = "#215E92"
MINT = "#1F9E82"

# Light-to-dark steps of the same navy hue, for magnitude-only charts (a status
# breakdown, a top-N donut) where color encodes "how much", not "which series".
NAVY_SEQUENTIAL = ["#CDE0F0", "#9FC2DE", "#6FA3CB", "#3F84B8", "#215E92", "#164569"]

SURFACE = "#FCFCFB"
GRID = "#E1E0D9"
TEXT_PRIMARY = "#0B0B0B"
TEXT_MUTED = "#6B6A65"

FONT_FAMILY = "system-ui, -apple-system, 'Segoe UI', sans-serif"


def apply_layout(fig, title=None, height=420, showlegend=True):
    """Applies one consistent look to every chart in the app: same font, same
    muted gridlines, same margins - so the dashboard reads as one system rather
    than a pile of default-themed Plotly charts."""
    fig.update_layout(
        title=title,
        height=height,
        showlegend=showlegend,
        plot_bgcolor=SURFACE,
        paper_bgcolor=SURFACE,
        font=dict(family=FONT_FAMILY, color=TEXT_PRIMARY, size=13),
        title_font=dict(size=16, color=TEXT_PRIMARY),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        margin=dict(l=10, r=10, t=60 if title else 30, b=10),
        hoverlabel=dict(bgcolor="white", font_size=12, font_family=FONT_FAMILY),
    )
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
