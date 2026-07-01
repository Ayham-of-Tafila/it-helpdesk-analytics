"""
Pipeline orchestrator.

Runs the full ETL flow in order:

    generate -> extract -> transform -> load

Usage
-----
    python -m etl.run            # full run (regenerates raw data)
    python -m etl.run --no-generate   # reuse existing raw CSV

The root-level ``run_pipeline.py`` is a thin wrapper around this module.
"""

from __future__ import annotations

import argparse
import time

from etl import config, extract, generate_data, load, transform


def run_pipeline(regenerate: bool = True) -> dict[str, int]:
    """Execute the end-to-end pipeline and return the loaded row counts."""
    start = time.perf_counter()
    config.ensure_directories()

    print("=" * 64)
    print("  IT HELPDESK ANALYTICS — ETL PIPELINE")
    print("=" * 64)

    # 1) GENERATE ----------------------------------------------------------
    if regenerate or not config.RAW_TICKETS_CSV.exists():
        generate_data.main()
    else:
        print("[generate]  Skipped (reusing existing raw CSV)")

    # 2) EXTRACT -----------------------------------------------------------
    raw = extract.extract_raw_tickets()

    # 3) TRANSFORM ---------------------------------------------------------
    clean = transform.transform_tickets(raw)
    clean.to_csv(config.CLEAN_TICKETS_CSV, index=False)
    print(
        f"[transform] Wrote clean CSV -> "
        f"{config.CLEAN_TICKETS_CSV.relative_to(config.PROJECT_ROOT)}"
    )

    # 4) LOAD --------------------------------------------------------------
    row_counts = load.load_to_sqlite(clean)

    elapsed = time.perf_counter() - start
    print("-" * 64)
    print(f"  Pipeline finished in {elapsed:0.2f}s. "
          f"Database ready at {config.DATABASE_PATH.name}")
    print("=" * 64)
    return row_counts


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the IT helpdesk ETL pipeline.")
    parser.add_argument(
        "--no-generate",
        action="store_true",
        help="Reuse the existing raw CSV instead of regenerating it.",
    )
    args = parser.parse_args()
    run_pipeline(regenerate=not args.no_generate)


if __name__ == "__main__":
    main()
