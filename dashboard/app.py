"""
IT Helpdesk Analytics — Streamlit dashboard.

An interactive front-end over the SQLite warehouse built by the ETL pipeline.
It provides headline KPIs, trend charts, category/priority breakdowns, an agent
leaderboard and sidebar filters (date range, category, priority, department).

Run with:
    streamlit run dashboard/app.py

The dashboard reads the denormalised fact frame once (cached) and applies the
sidebar filters client-side with pandas, which keeps interactions snappy while
still demonstrating the underlying SQL via the "SQL behind this page" expander.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

# Make the sibling `queries` module importable when run via `streamlit run`.
sys.path.append(str(Path(__file__).resolve().parent))
import queries  # noqa: E402

# --- Page config -----------------------------------------------------------
st.set_page_config(
    page_title="IT Helpdesk Analytics",
    page_icon="🛠️",
    layout="wide",
    initial_sidebar_state="expanded",
)

PRIORITY_ORDER = ["Low", "Medium", "High", "Critical"]
PLOTLY_TEMPLATE = "plotly_white"


@st.cache_data(show_spinner=False)
def get_data() -> pd.DataFrame:
    """Load and lightly type the fact frame (cached for the session)."""
    df = queries.load_fact_frame()
    df["full_date"] = pd.to_datetime(df["full_date"])
    df["month_start"] = pd.to_datetime(df["month_start"])
    return df


def kpi_card(label: str, value: str, help_text: str = "") -> None:
    """Render a single KPI metric."""
    st.metric(label, value, help=help_text)


def main() -> None:
    # --- Guard: has the pipeline been run? --------------------------------
    if not queries.database_exists():
        st.error(
            "No database found. Run the ETL pipeline first:\n\n"
            "```\npython run_pipeline.py\n```"
        )
        st.stop()

    df = get_data()

    # --- Header -----------------------------------------------------------
    st.title("🛠️ IT Helpdesk Analytics Dashboard")
    st.caption(
        "End-to-end ETL demo — synthetic support tickets cleaned with pandas, "
        "modelled in a SQLite star schema, and served over SQL. "
        "Built by Ayham Al-Mahasneh."
    )

    # --- Sidebar filters --------------------------------------------------
    st.sidebar.header("Filters")

    min_date = df["full_date"].min().date()
    max_date = df["full_date"].max().date()
    date_range = st.sidebar.date_input(
        "Date range",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
    )

    categories = sorted(df["category"].unique())
    sel_categories = st.sidebar.multiselect(
        "Category", categories, default=categories
    )

    priorities = [p for p in PRIORITY_ORDER if p in df["priority"].unique()]
    sel_priorities = st.sidebar.multiselect(
        "Priority", priorities, default=priorities
    )

    departments = sorted(df["department"].unique())
    sel_departments = st.sidebar.multiselect(
        "Department", departments, default=departments
    )

    st.sidebar.markdown("---")
    st.sidebar.caption(
        "Data is synthetic and generated deterministically "
        "(seed = 42) by `etl/generate_data.py`."
    )

    # --- Apply filters ----------------------------------------------------
    if isinstance(date_range, tuple) and len(date_range) == 2:
        start, end = date_range
    else:  # single date fallback
        start = end = date_range if not isinstance(date_range, tuple) else date_range[0]

    mask = (
        (df["full_date"].dt.date >= start)
        & (df["full_date"].dt.date <= end)
        & (df["category"].isin(sel_categories))
        & (df["priority"].isin(sel_priorities))
        & (df["department"].isin(sel_departments))
    )
    fdf = df[mask]

    if fdf.empty:
        st.warning("No tickets match the selected filters.")
        st.stop()

    # --- KPI row ----------------------------------------------------------
    total = len(fdf)
    resolved = int(fdf["is_resolved"].sum())
    resolved_pct = 100.0 * resolved / total if total else 0
    avg_res = fdf["resolution_hours"].mean()
    breach_pct = (
        100.0 * fdf["sla_breached"].sum() / resolved if resolved else 0
    )
    avg_csat = fdf["satisfaction_score"].mean()

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        kpi_card("Total Tickets", f"{total:,}")
    with c2:
        kpi_card("Resolved", f"{resolved_pct:.1f}%", f"{resolved:,} tickets")
    with c3:
        kpi_card("Avg Resolution", f"{avg_res:.1f} h")
    with c4:
        kpi_card("SLA Breach Rate", f"{breach_pct:.1f}%",
                 "Share of resolved tickets slower than their SLA target")
    with c5:
        kpi_card("Avg CSAT", f"{avg_csat:.2f} / 5")

    st.markdown("---")

    # --- Row 1: trend + category -----------------------------------------
    left, right = st.columns((3, 2))

    with left:
        st.subheader("Ticket volume over time")
        monthly = (
            fdf.groupby("month_start")
            .agg(tickets=("ticket_id", "count"),
                 breaches=("sla_breached", "sum"))
            .reset_index()
            .sort_values("month_start")
        )
        monthly["rolling_3mo"] = (
            monthly["tickets"].rolling(3, min_periods=1).mean().round(0)
        )
        fig = px.line(
            monthly,
            x="month_start",
            y="tickets",
            markers=True,
            template=PLOTLY_TEMPLATE,
            labels={"month_start": "Month", "tickets": "Tickets"},
        )
        fig.add_scatter(
            x=monthly["month_start"],
            y=monthly["rolling_3mo"],
            mode="lines",
            name="3-month avg",
            line=dict(dash="dash"),
        )
        fig.update_layout(margin=dict(t=10, b=0, l=0, r=0), height=340,
                          legend=dict(orientation="h", y=1.1))
        st.plotly_chart(fig, use_container_width=True)

    with right:
        st.subheader("Tickets by category")
        by_cat = (
            fdf.groupby("category")
            .size()
            .reset_index(name="tickets")
            .sort_values("tickets", ascending=True)
        )
        fig = px.bar(
            by_cat,
            x="tickets",
            y="category",
            orientation="h",
            template=PLOTLY_TEMPLATE,
            color="tickets",
            color_continuous_scale="Blues",
        )
        fig.update_layout(margin=dict(t=10, b=0, l=0, r=0), height=340,
                          coloraxis_showscale=False)
        st.plotly_chart(fig, use_container_width=True)

    # --- Row 2: priority SLA + channel -----------------------------------
    left2, right2 = st.columns(2)

    with left2:
        st.subheader("Avg resolution vs SLA target by priority")
        by_pri = (
            fdf.groupby("priority")
            .agg(avg_res=("resolution_hours", "mean"),
                 sla_target=("sla_target_hours", "first"))
            .reindex([p for p in PRIORITY_ORDER if p in fdf["priority"].unique()])
            .reset_index()
        )
        fig = px.bar(
            by_pri.melt(id_vars="priority",
                        value_vars=["avg_res", "sla_target"],
                        var_name="metric", value_name="hours"),
            x="priority",
            y="hours",
            color="metric",
            barmode="group",
            template=PLOTLY_TEMPLATE,
            labels={"hours": "Hours", "priority": "Priority"},
        )
        fig.for_each_trace(
            lambda t: t.update(name={"avg_res": "Actual avg",
                                     "sla_target": "SLA target"}[t.name])
        )
        fig.update_layout(margin=dict(t=10, b=0, l=0, r=0), height=340,
                          legend=dict(orientation="h", y=1.1))
        st.plotly_chart(fig, use_container_width=True)

    with right2:
        st.subheader("Tickets by channel")
        by_ch = fdf.groupby("channel").size().reset_index(name="tickets")
        fig = px.pie(
            by_ch, names="channel", values="tickets", hole=0.45,
            template=PLOTLY_TEMPLATE,
        )
        fig.update_layout(margin=dict(t=10, b=0, l=0, r=0), height=340)
        st.plotly_chart(fig, use_container_width=True)

    # --- Row 3: agent leaderboard ----------------------------------------
    st.subheader("Agent performance leaderboard")
    leaderboard = (
        fdf.groupby("agent")
        .agg(
            assigned=("ticket_id", "count"),
            resolved=("is_resolved", "sum"),
            avg_resolution_h=("resolution_hours", "mean"),
            sla_breaches=("sla_breached", "sum"),
            avg_csat=("satisfaction_score", "mean"),
        )
        .reset_index()
    )
    leaderboard["sla_breach_pct"] = (
        100.0 * leaderboard["sla_breaches"] / leaderboard["resolved"].clip(lower=1)
    )
    leaderboard = leaderboard.sort_values("resolved", ascending=False)
    leaderboard.insert(0, "rank", range(1, len(leaderboard) + 1))
    st.dataframe(
        leaderboard[
            ["rank", "agent", "assigned", "resolved",
             "avg_resolution_h", "sla_breach_pct", "avg_csat"]
        ].style.format(
            {
                "avg_resolution_h": "{:.1f}",
                "sla_breach_pct": "{:.1f}%",
                "avg_csat": "{:.2f}",
            }
        ),
        use_container_width=True,
        hide_index=True,
    )

    # --- Transparency: show the SQL --------------------------------------
    with st.expander("🔎 SQL behind this dashboard"):
        st.markdown(
            "These queries live in the project's `sql/` folder and power the "
            "server-side views. The interactive charts above apply the sidebar "
            "filters in pandas for responsiveness."
        )
        for q in ("kpi_summary", "tickets_by_month",
                  "resolution_by_category", "agent_leaderboard",
                  "sla_by_priority"):
            st.markdown(f"**`sql/{q}.sql`**")
            st.code(queries.load_sql(q), language="sql")


if __name__ == "__main__":
    main()
