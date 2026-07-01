"""
Transform stage.

This is where the real data-engineering happens. Given the raw, messy ticket
frame from the Extract stage, we:

  1. Drop exact duplicate rows.
  2. Normalise text fields (trim whitespace, fix inconsistent casing).
  3. Coerce types (parse timestamps and numeric columns).
  4. Compute the derived ``resolution_hours`` metric.
  5. Validate rows and discard the impossible ones
     (resolved-before-created, unparseable dates).
  6. Enrich with date-dimension columns and SLA flags used by the dashboard.

Each function is small and pure so it can be unit-tested in isolation
(see ``tests/test_transform.py``).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from etl import config

# Canonical category names, lower-cased, for normalising dirty input.
_CANONICAL_CATEGORIES = {c.lower(): c for c in config.CATEGORIES}


def drop_duplicates(df: pd.DataFrame) -> pd.DataFrame:
    """Remove exact duplicate rows, keeping the first occurrence."""
    before = len(df)
    df = df.drop_duplicates().reset_index(drop=True)
    print(f"[transform] Dropped {before - len(df):,} duplicate rows")
    return df


def normalise_text(df: pd.DataFrame) -> pd.DataFrame:
    """Trim whitespace and restore canonical casing on categorical columns."""
    df = df.copy()

    # Category: strip, collapse case, map back to the canonical label.
    df["category"] = (
        df["category"].str.strip().str.lower().map(_CANONICAL_CATEGORIES)
    )

    # Simple strip on the remaining free-text-ish columns.
    for col in ("priority", "channel", "department", "agent"):
        df[col] = df[col].str.strip()

    return df


def coerce_types(df: pd.DataFrame) -> pd.DataFrame:
    """
    Parse timestamps and numeric columns.

    Empty strings become NaT/NaN. Unparseable values are coerced to NaT/NaN so
    they can be filtered out in :func:`validate`.
    """
    df = df.copy()
    df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce")
    # Empty string -> NaT (open tickets have no resolved_at).
    df["resolved_at"] = pd.to_datetime(
        df["resolved_at"].replace("", np.nan), errors="coerce"
    )
    df["satisfaction_score"] = pd.to_numeric(
        df["satisfaction_score"].replace("", np.nan), errors="coerce"
    )
    return df


def add_resolution_hours(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add ``resolution_hours`` = (resolved_at - created_at) in hours.

    Open tickets (no ``resolved_at``) get NaN. Value is rounded to 2 dp.
    """
    df = df.copy()
    delta = df["resolved_at"] - df["created_at"]
    df["resolution_hours"] = (delta.dt.total_seconds() / 3600.0).round(2)
    return df


def validate(df: pd.DataFrame) -> pd.DataFrame:
    """
    Drop rows that fail integrity checks:

      * missing or unparseable ``created_at``
      * unknown category (failed to map to a canonical label)
      * negative ``resolution_hours`` (resolved before it was created)
    """
    before = len(df)

    valid_created = df["created_at"].notna()
    valid_category = df["category"].notna()
    # Keep open tickets (NaN hours); only drop the ones that are negative.
    non_negative = ~(df["resolution_hours"] < 0)

    df = df[valid_created & valid_category & non_negative].reset_index(drop=True)
    print(f"[transform] Dropped {before - len(df):,} invalid rows during validation")
    return df


def enrich(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add analytical helper columns used across the SQL queries and dashboard:

      * date-dimension fields (date, year, month, month_name, day_of_week, hour)
      * ``is_resolved`` flag
      * ``sla_target_hours`` looked up from priority
      * ``sla_breached`` flag (resolved slower than the SLA target)
    """
    df = df.copy()

    created = df["created_at"]
    df["created_date"] = created.dt.date.astype(str)
    df["created_year"] = created.dt.year
    df["created_month"] = created.dt.month
    df["created_month_start"] = created.dt.to_period("M").dt.to_timestamp().dt.date.astype(str)
    df["created_month_name"] = created.dt.strftime("%b %Y")
    df["created_day_of_week"] = created.dt.day_name()
    df["created_hour"] = created.dt.hour

    df["is_resolved"] = df["resolved_at"].notna()

    df["sla_target_hours"] = df["priority"].map(config.SLA_TARGET_HOURS)
    # A ticket breaches SLA only if it is resolved AND slower than its target.
    df["sla_breached"] = df["is_resolved"] & (
        df["resolution_hours"] > df["sla_target_hours"]
    )

    return df


def transform_tickets(raw: pd.DataFrame) -> pd.DataFrame:
    """
    Run the full transform pipeline on a raw ticket frame.

    This is the single entry point the Load stage and the orchestrator call.
    """
    df = drop_duplicates(raw)
    df = normalise_text(df)
    df = coerce_types(df)
    df = add_resolution_hours(df)
    df = validate(df)
    df = enrich(df)

    # Stable, human-friendly column order for the processed CSV.
    ordered = [
        "ticket_id",
        "created_at",
        "resolved_at",
        "created_date",
        "created_month_start",
        "created_month_name",
        "created_year",
        "created_month",
        "created_day_of_week",
        "created_hour",
        "category",
        "priority",
        "channel",
        "department",
        "agent",
        "is_resolved",
        "resolution_hours",
        "sla_target_hours",
        "sla_breached",
        "satisfaction_score",
    ]
    df = df[ordered]
    print(f"[transform] Produced {len(df):,} clean rows with {len(df.columns)} columns")
    return df
