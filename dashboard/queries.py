"""
Thin data-access layer for the dashboard.

Loads the ``.sql`` files from the project's ``sql/`` folder and runs them
against the SQLite database. Keeping the SQL in files (rather than inline
strings) means the analytical queries are first-class, reviewable artefacts —
which is the whole point of showcasing SQL skill in this project.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd

# Resolve project paths without importing the etl package, so the dashboard can
# run standalone from anywhere.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
SQL_DIR = PROJECT_ROOT / "sql"
DB_PATH = PROJECT_ROOT / "data" / "helpdesk.db"


def load_sql(name: str) -> str:
    """Read a named query (without the .sql extension) from the sql/ folder."""
    path = SQL_DIR / f"{name}.sql"
    return path.read_text(encoding="utf-8")


def run_query(name: str, params: tuple | None = None) -> pd.DataFrame:
    """Execute a named .sql file and return the result as a DataFrame."""
    sql = load_sql(name)
    with sqlite3.connect(DB_PATH) as conn:
        return pd.read_sql_query(sql, conn, params=params)


def load_fact_frame() -> pd.DataFrame:
    """
    Load the full denormalised fact table (joined to its dimensions) for the
    interactive, client-side filters in the dashboard.
    """
    sql = """
        SELECT
            f.ticket_id,
            d.full_date,
            d.month_start,
            d.month_name,
            d.year,
            c.category_name  AS category,
            p.priority_name  AS priority,
            p.sla_target_hours,
            a.agent_name     AS agent,
            f.channel,
            f.department,
            f.created_hour,
            f.is_resolved,
            f.resolution_hours,
            f.sla_breached,
            f.satisfaction_score
        FROM fact_tickets AS f
        JOIN dim_date     AS d ON f.date_key = d.date_key
        JOIN dim_category AS c ON f.category_key = c.category_key
        JOIN dim_priority AS p ON f.priority_key = p.priority_key
        JOIN dim_agent    AS a ON f.agent_key = a.agent_key
    """
    with sqlite3.connect(DB_PATH) as conn:
        return pd.read_sql_query(sql, conn)


def database_exists() -> bool:
    """True if the pipeline has been run and the database is present."""
    return DB_PATH.exists()
