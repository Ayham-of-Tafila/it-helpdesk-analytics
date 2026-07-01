"""
Extract stage.

Reads the raw ticket CSV into a pandas DataFrame. In a production system this
is where you would connect to source APIs, message queues, or an operational
database; here the "source" is the CSV produced by ``generate_data.py``.

The stage is deliberately thin — it only *reads* and does no cleaning, so the
separation of concerns between Extract and Transform stays crisp.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from etl import config


def extract_raw_tickets(path: Path | None = None) -> pd.DataFrame:
    """
    Load raw tickets from CSV.

    Parameters
    ----------
    path:
        Optional override for the raw CSV location (useful in tests).

    Returns
    -------
    pandas.DataFrame
        The raw, untouched ticket data.
    """
    source = path or config.RAW_TICKETS_CSV
    if not source.exists():
        raise FileNotFoundError(
            f"Raw data not found at {source}. Run `python -m etl.generate_data` "
            "first (or use the full pipeline)."
        )

    # Read everything as string so the Transform stage owns all type coercion.
    df = pd.read_csv(source, dtype=str, keep_default_na=False)
    print(f"[extract]   Read {len(df):,} raw rows from {source.name}")
    return df
