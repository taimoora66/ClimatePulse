from __future__ import annotations

import html

import pandas as pd
import streamlit as st


def inject_v27_ui():
    """
    Global visual refinement for ClimatePulse.

    Keeps the existing identity, but removes default white/flat Streamlit
    surfaces that conflict with the dark climate-intelligence interface.
    """
    st.html(
        """
<style>
:root {
    --cp27-bg: #020d15;
    --cp27-surface: #061a26;
    --cp27-surface-2: #092230;
    --cp27-cyan: #52dcff;
    --cp27-text: #eefaff;
    --cp27-muted: #7899a9;
    --cp27-border: rgba(78, 220, 249, .13);
}

/* App background */
[data-testid="stAppViewContainer"] {
    background:
        radial-gradient(
            circle at 73% 0%,
            rgba(25, 112, 137, .09),
            transparent 28rem
        ),
        radial-gradient(
            circle at 35% 110%,
            rgba(25, 83, 119, .06),
            transparent 34rem
        ),
        linear-gradient(
            180deg,
            #03111b 0%,
            #020b12 100%
        ) !important;
}

[data-testid="stHeader"] {
    background: rgba(2, 10, 17, .75) !important;
    backdrop-filter: blur(12px);
}

/* Main content breathes more consistently */
[data-testid="stMainBlockContainer"] {
    padding-top: 1.1rem;
}

/* Sidebar */
[data-testid="stSidebar"] {
    border-right: 1px solid rgba(79, 218, 247, .09);
    background:
        linear-gradient(
            180deg,
            #020d15,
            #020b12
        ) !important;
}

/* Native metric cards */
[data-testid="stMetric"] {
    border-radius: 14px;
    border: 1px solid var(--cp27-border);
    background:
        linear-gradient(
            145deg,
            rgba(8, 31, 44, .96),
            rgba(5, 20, 30, .94)
        );
    padding: 12px 13px;
}

[data-testid="stMetricLabel"] {
    color: #7394a4 !important;
}

[data-testid="stMetricValue"] {
    color: #f2fbff !important;
    font-weight: 820 !important;
    letter-spacing: -.025em;
}

[data-testid="stMetricDelta"] {
    color: #55ddb4 !important;
}

/* Plotly charts read as polished analytical surfaces */
[data-testid="stPlotlyChart"] {
    border-radius: 17px;
    border: 1px solid rgba(76, 215, 246, .09);
    background:
        linear-gradient(
            145deg,
            rgba(7, 27, 39, .83),
            rgba(4, 17, 27, .76)
        );
    overflow: hidden;
}

/* Expander / bordered containers */
[data-testid="stExpander"],
[data-testid="stVerticalBlockBorderWrapper"] {
    border-color: rgba(75, 214, 244, .11) !important;
    border-radius: 14px !important;
}

/* Buttons */
.stButton button {
    border-radius: 11px !important;
    border-color: rgba(77, 219, 248, .18) !important;
}

/* Search/select controls */
[data-baseweb="select"] > div,
[data-testid="stTextInputRootElement"],
[data-testid="stTextAreaRootElement"] {
    border-color: rgba(79, 219, 248, .14) !important;
}

/* Typography */
h1, h2, h3 {
    letter-spacing: -.028em;
    color: #effbff !important;
}

.cp27-divider {
    height: 1px;
    margin: 10px 0 17px;
    background:
        linear-gradient(
            90deg,
            rgba(82, 220, 255, 0),
            rgba(82, 220, 255, .38),
            rgba(82, 220, 255, 0)
        );
}

.cp27-table-wrap {
    width: 100%;
    overflow-x: auto;
    border: 1px solid rgba(75, 214, 244, .12);
    border-radius: 14px;
    background: #061923;
}

.cp27-table {
    min-width: 100%;
    border-collapse: collapse;
    color: #dcecf3;
    font-size: .75rem;
}

.cp27-table th {
    padding: 10px 11px;
    text-align: left;
    white-space: nowrap;
    color: #8aabba;
    background: #0a2432;
    border-bottom: 1px solid rgba(75, 214, 244, .12);
    font-size: .68rem;
    font-weight: 760;
}

.cp27-table td {
    padding: 10px 11px;
    white-space: nowrap;
    color: #e4f1f6;
    background: rgba(6, 25, 36, .96);
    border-bottom: 1px solid rgba(75, 214, 244, .065);
}

.cp27-table tbody tr:hover td {
    background: rgba(11, 42, 57, .98);
}

.cp27-table tbody tr:last-child td {
    border-bottom: 0;
}

.cp27-none {
    color: #607d8b !important;
}

@media (max-width: 850px) {
    [data-testid="stMainBlockContainer"] {
        padding-left: .85rem;
        padding-right: .85rem;
    }
}
</style>
        """
    )


def _cell(value):
    if value is None:
        return (
            '<span class="cp27-none">—</span>'
        )

    try:
        if pd.isna(value):
            return (
                '<span class="cp27-none">—</span>'
            )
    except Exception:
        pass

    if isinstance(
        value,
        float,
    ):
        text = f"{value:.2f}".rstrip(
            "0"
        ).rstrip(
            "."
        )
    else:
        text = str(
            value
        )

    return html.escape(
        text
    )


def dark_dataframe(
    frame,
):
    """
    Render compact dark analytical tables instead of Streamlit's white grid.
    """
    if (
        frame is None
        or frame.empty
    ):
        st.caption(
            "No data available."
        )
        return

    headers = "".join(
        f"<th>{html.escape(str(column))}</th>"
        for column in frame.columns
    )

    rows = []

    for _, row in frame.iterrows():
        rows.append(
            "<tr>"
            + "".join(
                f"<td>{_cell(value)}</td>"
                for value in row.tolist()
            )
            + "</tr>"
        )

    st.html(
        f"""
<div class="cp27-table-wrap">
  <table class="cp27-table">
    <thead><tr>{headers}</tr></thead>
    <tbody>{''.join(rows)}</tbody>
  </table>
</div>
        """
    )


def style_plotly_v27(
    figure,
):
    """
    Consistent analytical Plotly styling.
    """
    figure.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(
            color="#afc7d2",
        ),
        legend=dict(
            bgcolor="rgba(0,0,0,0)",
            font=dict(
                color="#89a6b4",
            ),
        ),
        hoverlabel=dict(
            bgcolor="#071d29",
            bordercolor="#2a8098",
            font=dict(
                color="#f4fbff",
            ),
        ),
    )

    figure.update_xaxes(
        showgrid=False,
        zeroline=False,
        tickfont=dict(
            color="#718e9d",
        ),
        title_font=dict(
            color="#87a3b0",
        ),
        linecolor="rgba(105,164,183,.15)",
    )

    figure.update_yaxes(
        showgrid=True,
        gridcolor="rgba(105,164,183,.09)",
        zeroline=False,
        tickfont=dict(
            color="#718e9d",
        ),
        title_font=dict(
            color="#87a3b0",
        ),
        linecolor="rgba(105,164,183,.15)",
    )

    return figure