"""
Load stage.

Writes the cleaned ticket frame into a SQLite database using a small star-ish
schema: one fact table (``fact_tickets``) referencing four dimension tables
(``dim_date``, ``dim_category``, ``dim_priority``, ``dim_agent``).

The schema is defined in ``sql/schema.sql`` so the DDL is visible and reviewable
rather than buried in Python string literals. This mirrors how a real warehouse
project keeps its SQL under version control.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd

from etl import config


def _build_dimensions(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Derive dimension tables (with surrogate keys) from the clean fact frame."""

    # --- dim_date : one row per calendar date present in the data ----------
    dim_date = (
        df[
            [
                "created_date",
                "created_month_start",
                "created_month_name",
                "created_year",
                "created_month",
                "created_day_of_week",
            ]
        ]
        .drop_duplicates(subset=["created_date"])
        .sort_values("created_date")
        .reset_index(drop=True)
    )
    dim_date.insert(0, "date_key", dim_date.index + 1)
    dim_date = dim_date.rename(
        columns={
            "created_date": "full_date",
            "created_month_start": "month_start",
            "created_month_name": "month_name",
            "created_year": "year",
            "created_month": "month",
            "created_day_of_week": "day_of_week",
        }
    )

    # --- dim_category ------------------------------------------------------
    dim_category = (
        pd.DataFrame({"category_name": sorted(df["category"].unique())})
        .reset_index(drop=True)
    )
    dim_category.insert(0, "category_key", dim_category.index + 1)

    # --- dim_priority (carries the SLA target as an attribute) -------------
    dim_priority = (
        df[["priority", "sla_target_hours"]]
        .drop_duplicates()
        .sort_values("sla_target_hours")
        .reset_index(drop=True)
        .rename(columns={"priority": "priority_name"})
    )
    dim_priority.insert(0, "priority_key", dim_priority.index + 1)

    # --- dim_agent ---------------------------------------------------------
    dim_agent = (
        pd.DataFrame({"agent_name": sorted(df["agent"].unique())})
        .reset_index(drop=True)
    )
    dim_agent.insert(0, "agent_key", dim_agent.index + 1)

    return {
        "dim_date": dim_date,
        "dim_category": dim_category,
        "dim_priority": dim_priority,
        "dim_agent": dim_agent,
    }


def _build_fact(df: pd.DataFrame, dims: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Map the natural keys in the clean frame onto dimension surrogate keys."""
    date_map = dict(
        zip(dims["dim_date"]["full_date"], dims["dim_date"]["date_key"])
    )
    category_map = dict(
        zip(dims["dim_category"]["category_name"], dims["dim_category"]["category_key"])
    )
    priority_map = dict(
        zip(dims["dim_priority"]["priority_name"], dims["dim_priority"]["priority_key"])
    )
    agent_map = dict(
        zip(dims["dim_agent"]["agent_name"], dims["dim_agent"]["agent_key"])
    )

    fact = pd.DataFrame(
        {
            "ticket_id": df["ticket_id"],
            "date_key": df["created_date"].map(date_map),
            "category_key": df["category"].map(category_map),
            "priority_key": df["priority"].map(priority_map),
            "agent_key": df["agent"].map(agent_map),
            "created_at": df["created_at"].astype(str),
            "resolved_at": df["resolved_at"].astype(str).replace("NaT", None),
            "channel": df["channel"],
            "department": df["department"],
            "created_hour": df["created_hour"],
            "is_resolved": df["is_resolved"].astype(int),
            "resolution_hours": df["resolution_hours"],
            "sla_breached": df["sla_breached"].astype(int),
            "satisfaction_score": df["satisfaction_score"],
        }
    )
    return fact


def load_to_sqlite(
    df: pd.DataFrame,
    db_path: Path | None = None,
    schema_path: Path | None = None,
) -> dict[str, int]:
    """
    Create the schema and load fact + dimension tables into SQLite.

    Returns a dict of ``{table_name: row_count}`` for verification/logging.
    """
    db_path = db_path or config.DATABASE_PATH
    schema_path = schema_path or config.SCHEMA_SQL

    dims = _build_dimensions(df)
    fact = _build_fact(df, dims)

    # Fresh build every run so the pipeline is idempotent.
    if db_path.exists():
        db_path.unlink()

    schema_sql = schema_path.read_text(encoding="utf-8")

    row_counts: dict[str, int] = {}
    with sqlite3.connect(db_path) as conn:
        conn.executescript(schema_sql)

        for name, frame in dims.items():
            frame.to_sql(name, conn, if_exists="append", index=False)
            row_counts[name] = len(frame)

        fact.to_sql("fact_tickets", conn, if_exists="append", index=False)
        row_counts["fact_tickets"] = len(fact)

        conn.commit()

    print(f"[load]      Wrote database -> {db_path.name}")
    for name, count in row_counts.items():
        print(f"[load]        {name:<16} {count:>7,} rows")
    return row_counts
