"""
Synthetic data generator for the IT helpdesk pipeline.

Rather than depend on a flaky external download, the project generates its own
realistic support-ticket dataset. The data is intentionally *messy* — it
contains duplicates, inconsistent casing, blank fields, and a handful of
tickets whose "resolved" timestamp precedes their "created" timestamp — so the
Transform stage has real cleaning work to do (exactly like production data).

Run standalone with:  python -m etl.generate_data
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

from etl import config


def _random_datetime(rng: random.Random, start: datetime, end: datetime) -> datetime:
    """Return a random datetime between ``start`` and ``end``."""
    delta_seconds = int((end - start).total_seconds())
    return start + timedelta(seconds=rng.randint(0, delta_seconds))


def generate_raw_tickets() -> pd.DataFrame:
    """
    Build a DataFrame of raw, deliberately-imperfect helpdesk tickets.

    The resolution time for each ticket is drawn from a log-normal
    distribution and scaled by category difficulty and priority urgency, so
    aggregate statistics (e.g. Security tickets take longer, Critical tickets
    are resolved fastest) look believable in the dashboard.
    """
    rng = random.Random(config.RANDOM_SEED)
    np.random.seed(config.RANDOM_SEED)

    start = datetime.fromisoformat(config.START_DATE)
    end = datetime.fromisoformat(config.END_DATE)

    categories = list(config.CATEGORIES.keys())
    priorities = list(config.PRIORITIES.keys())
    # Priority mix skewed toward Low/Medium, like a real support queue.
    priority_weights = [0.35, 0.40, 0.18, 0.07]

    records: list[dict] = []
    for i in range(1, config.N_TICKETS + 1):
        category = rng.choice(categories)
        priority = rng.choices(priorities, weights=priority_weights, k=1)[0]

        created = _random_datetime(rng, start, end)

        # Base resolution time (hours) from a log-normal distribution, then
        # scaled by how hard the category is and how urgent the priority is.
        base_hours = float(np.random.lognormal(mean=1.7, sigma=0.9))
        hours = base_hours * config.CATEGORIES[category] * config.PRIORITIES[priority]
        hours = round(min(hours, 720), 2)  # cap at 30 days

        # ~8% of tickets are still open (no resolution timestamp yet).
        is_open = rng.random() < 0.08
        resolved = None if is_open else created + timedelta(hours=hours)

        # Satisfaction score only exists for resolved tickets, and correlates
        # loosely (inversely) with how long the ticket took.
        satisfaction = None
        if resolved is not None:
            score = 5 - min(4, hours / 60) + rng.uniform(-0.6, 0.6)
            satisfaction = int(max(1, min(5, round(score))))

        # Introduce dirty formatting: random casing / whitespace on category.
        dirty_category = category
        roll = rng.random()
        if roll < 0.10:
            dirty_category = category.upper()
        elif roll < 0.20:
            dirty_category = f"  {category.lower()} "

        records.append(
            {
                "ticket_id": f"TK-{i:06d}",
                "created_at": created.strftime("%Y-%m-%d %H:%M:%S"),
                "resolved_at": (
                    resolved.strftime("%Y-%m-%d %H:%M:%S") if resolved else ""
                ),
                "category": dirty_category,
                "priority": priority,
                "channel": rng.choice(config.CHANNELS),
                "department": rng.choice(config.DEPARTMENTS),
                "agent": rng.choice(config.AGENTS),
                "satisfaction_score": (
                    "" if satisfaction is None else str(satisfaction)
                ),
            }
        )

    df = pd.DataFrame.from_records(records)

    # --- Inject data-quality problems for the Transform stage to fix --------
    # 1) Exact duplicate rows (~1.5%): same ticket logged twice.
    dup_sample = df.sample(frac=0.015, random_state=config.RANDOM_SEED)
    df = pd.concat([df, dup_sample], ignore_index=True)

    # 2) A few "impossible" tickets where resolved_at < created_at.
    bad_idx = df.sample(n=25, random_state=config.RANDOM_SEED).index
    for idx in bad_idx:
        created = datetime.strptime(df.at[idx, "created_at"], "%Y-%m-%d %H:%M:%S")
        df.at[idx, "resolved_at"] = (created - timedelta(hours=3)).strftime(
            "%Y-%m-%d %H:%M:%S"
        )

    # 3) Shuffle so duplicates/bad rows are not clustered at the end.
    df = df.sample(frac=1.0, random_state=config.RANDOM_SEED).reset_index(drop=True)
    return df


def main() -> None:
    """Generate the raw CSV and write it to ``data/raw/``."""
    config.ensure_directories()
    df = generate_raw_tickets()
    df.to_csv(config.RAW_TICKETS_CSV, index=False)
    print(
        f"[generate] Wrote {len(df):,} raw ticket rows -> "
        f"{config.RAW_TICKETS_CSV.relative_to(config.PROJECT_ROOT)}"
    )


if __name__ == "__main__":
    main()
