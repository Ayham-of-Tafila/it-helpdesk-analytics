"""
Central configuration and path management for the ETL pipeline.

Keeping every path in one place means the individual stages never hard-code
locations, and the whole project can be relocated without touching the logic.
"""

from __future__ import annotations

from pathlib import Path

# --- Directory layout -------------------------------------------------------
# PROJECT_ROOT resolves to the `data-pipeline-bi/` folder regardless of where
# the pipeline is launched from.
PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent

DATA_DIR: Path = PROJECT_ROOT / "data"
RAW_DIR: Path = DATA_DIR / "raw"
PROCESSED_DIR: Path = DATA_DIR / "processed"
SQL_DIR: Path = PROJECT_ROOT / "sql"

# --- Key files --------------------------------------------------------------
RAW_TICKETS_CSV: Path = RAW_DIR / "tickets_raw.csv"
CLEAN_TICKETS_CSV: Path = PROCESSED_DIR / "tickets_clean.csv"
DATABASE_PATH: Path = DATA_DIR / "helpdesk.db"
SCHEMA_SQL: Path = SQL_DIR / "schema.sql"

# --- Synthetic-data generation settings ------------------------------------
# Deterministic seed so every run produces the same dataset — important for a
# portfolio project where the numbers in the README should match the app.
RANDOM_SEED: int = 42
N_TICKETS: int = 8000
START_DATE: str = "2022-01-01"
END_DATE: str = "2024-12-31"

# --- Reference / business dimensions ---------------------------------------
# Categories with a "difficulty" weight that nudges resolution times so the
# generated data has realistic structure rather than pure noise.
CATEGORIES: dict[str, float] = {
    "Hardware": 1.4,
    "Software": 1.0,
    "Network": 1.6,
    "Account & Access": 0.6,
    "Email": 0.8,
    "Security": 1.8,
    "Printing": 0.7,
}

PRIORITIES: dict[str, float] = {
    "Low": 1.5,
    "Medium": 1.0,
    "High": 0.6,
    "Critical": 0.35,
}

# SLA resolution targets in hours, keyed by priority. A ticket "breaches" SLA
# when its resolution time exceeds the target for its priority.
SLA_TARGET_HOURS: dict[str, int] = {
    "Low": 72,
    "Medium": 24,
    "High": 8,
    "Critical": 4,
}

CHANNELS: list[str] = ["Email", "Phone", "Web Portal", "Walk-in", "Chat"]

DEPARTMENTS: list[str] = [
    "Finance",
    "HR",
    "Sales",
    "Operations",
    "IT",
    "Marketing",
    "Logistics",
]

AGENTS: list[str] = [
    "Ayham Al-Mahasneh",
    "Sara Khoury",
    "Omar Nasser",
    "Lina Haddad",
    "Yousef Barakat",
    "Maya Suleiman",
    "Tariq Odeh",
    "Rana Aziz",
]


def ensure_directories() -> None:
    """Create the data sub-directories if they do not already exist."""
    for directory in (RAW_DIR, PROCESSED_DIR):
        directory.mkdir(parents=True, exist_ok=True)
