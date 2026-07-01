"""
Unit tests for the Transform stage.

These focus on the pieces most likely to break silently and corrupt the
warehouse: duplicate removal, text normalisation, the derived resolution-time
metric, validation of impossible rows, and SLA-breach enrichment.

Run with:  pytest -q
"""

from __future__ import annotations

import pandas as pd
import pytest

from etl import transform


def _raw_frame(rows: list[dict]) -> pd.DataFrame:
    """Helper: build a raw-style (all-string) frame with the expected columns."""
    columns = [
        "ticket_id", "created_at", "resolved_at", "category", "priority",
        "channel", "department", "agent", "satisfaction_score",
    ]
    return pd.DataFrame(rows, columns=columns).astype(str)


# --- drop_duplicates -------------------------------------------------------
def test_drop_duplicates_removes_exact_copies():
    row = {
        "ticket_id": "TK-1", "created_at": "2023-01-01 09:00:00",
        "resolved_at": "2023-01-01 12:00:00", "category": "Network",
        "priority": "Medium", "channel": "Email", "department": "IT",
        "agent": "Sara Khoury", "satisfaction_score": "4",
    }
    df = _raw_frame([row, row, {**row, "ticket_id": "TK-2"}])
    out = transform.drop_duplicates(df)
    assert len(out) == 2  # one exact dup removed, distinct row kept


# --- normalise_text --------------------------------------------------------
def test_normalise_text_canonicalises_category_casing_and_whitespace():
    df = _raw_frame(
        [
            {"ticket_id": "TK-1", "created_at": "2023-01-01 09:00:00",
             "resolved_at": "", "category": "  network ", "priority": "Low",
             "channel": "Chat", "department": "HR", "agent": "Omar Nasser",
             "satisfaction_score": ""},
            {"ticket_id": "TK-2", "created_at": "2023-01-01 09:00:00",
             "resolved_at": "", "category": "HARDWARE", "priority": "High",
             "channel": "Phone", "department": "Sales", "agent": "Lina Haddad",
             "satisfaction_score": ""},
        ]
    )
    out = transform.normalise_text(df)
    assert list(out["category"]) == ["Network", "Hardware"]


# --- resolution_hours ------------------------------------------------------
def test_resolution_hours_computed_correctly():
    df = _raw_frame(
        [{"ticket_id": "TK-1", "created_at": "2023-03-01 08:00:00",
          "resolved_at": "2023-03-01 13:30:00", "category": "Software",
          "priority": "Medium", "channel": "Web Portal", "department": "IT",
          "agent": "Maya Suleiman", "satisfaction_score": "5"}]
    )
    df = transform.coerce_types(df)
    out = transform.add_resolution_hours(df)
    assert out["resolution_hours"].iloc[0] == pytest.approx(5.5)


def test_open_ticket_has_nan_resolution_hours():
    df = _raw_frame(
        [{"ticket_id": "TK-1", "created_at": "2023-03-01 08:00:00",
          "resolved_at": "", "category": "Email", "priority": "Low",
          "channel": "Email", "department": "Finance", "agent": "Tariq Odeh",
          "satisfaction_score": ""}]
    )
    df = transform.coerce_types(df)
    out = transform.add_resolution_hours(df)
    assert pd.isna(out["resolution_hours"].iloc[0])


# --- validate --------------------------------------------------------------
def test_validate_drops_resolved_before_created():
    df = _raw_frame(
        [
            {"ticket_id": "TK-good", "created_at": "2023-01-01 09:00:00",
             "resolved_at": "2023-01-01 10:00:00", "category": "Network",
             "priority": "Medium", "channel": "Email", "department": "IT",
             "agent": "Rana Aziz", "satisfaction_score": "4"},
            {"ticket_id": "TK-bad", "created_at": "2023-01-01 09:00:00",
             "resolved_at": "2023-01-01 06:00:00", "category": "Network",
             "priority": "Medium", "channel": "Email", "department": "IT",
             "agent": "Rana Aziz", "satisfaction_score": "4"},
        ]
    )
    df = transform.normalise_text(df)
    df = transform.coerce_types(df)
    df = transform.add_resolution_hours(df)
    out = transform.validate(df)
    assert list(out["ticket_id"]) == ["TK-good"]


def test_validate_drops_unknown_category():
    df = _raw_frame(
        [{"ticket_id": "TK-1", "created_at": "2023-01-01 09:00:00",
          "resolved_at": "2023-01-01 10:00:00", "category": "Teleportation",
          "priority": "Low", "channel": "Chat", "department": "IT",
          "agent": "Omar Nasser", "satisfaction_score": "3"}]
    )
    df = transform.normalise_text(df)
    df = transform.coerce_types(df)
    df = transform.add_resolution_hours(df)
    out = transform.validate(df)
    assert out.empty


# --- enrich / SLA ----------------------------------------------------------
def test_sla_breach_flag_true_when_slower_than_target():
    # High priority target = 8h; this ticket took 10h -> breach.
    df = _raw_frame(
        [{"ticket_id": "TK-1", "created_at": "2023-01-01 00:00:00",
          "resolved_at": "2023-01-01 10:00:00", "category": "Security",
          "priority": "High", "channel": "Phone", "department": "IT",
          "agent": "Yousef Barakat", "satisfaction_score": "2"}]
    )
    out = transform.transform_tickets(df)
    assert bool(out["sla_breached"].iloc[0]) is True
    assert out["sla_target_hours"].iloc[0] == 8


def test_sla_breach_flag_false_when_within_target():
    # Low priority target = 72h; this ticket took 5h -> no breach.
    df = _raw_frame(
        [{"ticket_id": "TK-1", "created_at": "2023-01-01 00:00:00",
          "resolved_at": "2023-01-01 05:00:00", "category": "Printing",
          "priority": "Low", "channel": "Walk-in", "department": "HR",
          "agent": "Sara Khoury", "satisfaction_score": "5"}]
    )
    out = transform.transform_tickets(df)
    assert bool(out["sla_breached"].iloc[0]) is False


def test_full_transform_produces_expected_columns():
    df = _raw_frame(
        [{"ticket_id": "TK-1", "created_at": "2023-06-15 14:00:00",
          "resolved_at": "2023-06-16 14:00:00", "category": "software",
          "priority": "Medium", "channel": "Email", "department": "Marketing",
          "agent": "Maya Suleiman", "satisfaction_score": "4"}]
    )
    out = transform.transform_tickets(df)
    for col in ("resolution_hours", "sla_breached", "created_month_name",
                "is_resolved", "created_day_of_week"):
        assert col in out.columns
    assert out["resolution_hours"].iloc[0] == pytest.approx(24.0)
