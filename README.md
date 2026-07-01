# 🛠️ IT Helpdesk Analytics — Data Pipeline & Dashboard

An end-to-end **data-engineering + analytics** project: a Python ETL pipeline
that generates realistic IT support-ticket data, cleans and validates it with
**pandas**, models it in a **SQLite star schema**, and serves it through an
interactive **Streamlit + Plotly** dashboard powered by hand-written
analytical **SQL**.

I built this to reinforce the SQL-optimisation and Power BI reporting work I do
in my IT role. Because Power BI is proprietary and can't be demoed on GitHub, I
rebuilt the same idea with a fully open-source, self-contained stack that
anyone can clone and run in under a minute.

> **Author:** Ayham Al-Mahasneh — Computer Science student, applying for UK
> software / IT / data internships.

---

## ✨ Highlights

- **End-to-end ETL in one command** — `python run_pipeline.py` runs
  generate → extract → transform → load and builds a ready-to-query database
  from scratch (~8,000 tickets across 3 years) in under a second.
- **Real data-cleaning, not a toy** — the generator injects duplicates,
  inconsistent casing/whitespace, open tickets, and *impossible* rows
  (resolved-before-created); the transform stage dedups, coerces types,
  derives resolution time, validates integrity, and enriches with a date
  dimension + SLA-breach flags.
- **SQL front-and-centre** — a dimensional (star) schema plus six reusable
  `.sql` analytical queries using **joins, window functions
  (`RANK`, rolling `AVG OVER`), and conditional aggregation** — the same
  queries drive the dashboard and are viewable inside the app.
- **Tested & verified** — 9 `pytest` cases cover the transform logic; the
  pipeline and tests are proven to run green.

---

## 🏗️ Architecture

```
                    ┌──────────────────────────────────────────────┐
                    │                run_pipeline.py                │
                    │            (orchestrator: etl/run.py)         │
                    └──────────────────────────────────────────────┘
                                        │
   ┌───────────┐    ┌───────────┐    ┌───────────┐    ┌───────────┐
   │ GENERATE  │ -> │  EXTRACT  │ -> │ TRANSFORM │ -> │   LOAD    │
   │           │    │           │    │           │    │           │
   │ synthetic │    │ read raw  │    │ pandas:   │    │ SQLite    │
   │ tickets   │    │ CSV       │    │ dedup,    │    │ star      │
   │ (messy)   │    │ (strings) │    │ clean,    │    │ schema    │
   │           │    │           │    │ validate, │    │ fact+dims │
   │           │    │           │    │ enrich    │    │           │
   └───────────┘    └───────────┘    └───────────┘    └───────────┘
   data/raw/         DataFrame        data/processed/   data/helpdesk.db
   tickets_raw.csv                    tickets_clean.csv         │
                                                                 ▼
                                              ┌─────────────────────────────┐
                                              │   Streamlit + Plotly app    │
                                              │   (dashboard/app.py)        │
                                              │   KPIs · trends · SLA ·     │
                                              │   agent leaderboard         │
                                              │   ← reads sql/*.sql         │
                                              └─────────────────────────────┘
```

---

## 🧱 Data model (star schema)

One fact table surrounded by four conformed dimensions (DDL in
[`sql/schema.sql`](sql/schema.sql)):

| Table            | Grain / role                        | Key columns |
|------------------|-------------------------------------|-------------|
| `fact_tickets`   | one row per support ticket          | `ticket_id`, FKs, `resolution_hours`, `is_resolved`, `sla_breached`, `satisfaction_score` |
| `dim_date`       | one row per calendar date           | `date_key`, `full_date`, `month_name`, `year`, `day_of_week` |
| `dim_category`   | ticket categories                   | `category_key`, `category_name` |
| `dim_priority`   | priority tier + its SLA target      | `priority_key`, `priority_name`, `sla_target_hours` |
| `dim_agent`      | support agents                      | `agent_key`, `agent_name` |

**Fields engineered in the Transform stage:** `resolution_hours`
(= resolved − created), `is_resolved`, `sla_target_hours` (by priority),
`sla_breached` (resolved slower than target), plus a full set of date-dimension
attributes (`month_name`, `day_of_week`, `created_hour`, …).

**SLA targets:** Critical 4h · High 8h · Medium 24h · Low 72h.

---

## 🔑 Key SQL queries

All queries live in [`sql/`](sql/) and are loaded by name at runtime:

| File | What it demonstrates |
|------|----------------------|
| [`kpi_summary.sql`](sql/kpi_summary.sql) | headline KPIs via conditional aggregation (`SUM(is_resolved)`, breach rate with `NULLIF`) |
| [`tickets_by_month.sql`](sql/tickets_by_month.sql) | JOIN to `dim_date` + **window function** — 3-month rolling `AVG() OVER (ORDER BY … ROWS BETWEEN 2 PRECEDING AND CURRENT ROW)` |
| [`agent_leaderboard.sql`](sql/agent_leaderboard.sql) | **`RANK() OVER (...)`** leaderboard with multi-metric aggregation |
| [`resolution_by_category.sql`](sql/resolution_by_category.sql) | per-category volume, avg resolution, breach rate, CSAT |
| [`sla_by_priority.sql`](sql/sla_by_priority.sql) | SLA compliance per tier + share-of-total via `SUM(COUNT(*)) OVER ()` |
| [`tickets_by_channel_department.sql`](sql/tickets_by_channel_department.sql) | channel × department breakdown |

---

## 🚀 Setup & run

**Prerequisites:** Python 3.10+ (developed on 3.13).

```bash
# 1. Clone and enter the project
cd data-pipeline-bi

# 2. Create a virtual environment
python -m venv .venv

# Windows (PowerShell)
.venv\Scripts\Activate.ps1
# macOS / Linux
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the full ETL pipeline (generate → extract → transform → load)
python run_pipeline.py

# 5. Launch the interactive dashboard
streamlit run dashboard/app.py
```

The dashboard opens at `http://localhost:8501`.

**Run the tests:**

```bash
pytest
```

---

## 📊 Dashboard

The Streamlit app (`dashboard/app.py`) provides:

- **KPI header** — total tickets, resolved %, average resolution time,
  SLA-breach rate, average CSAT.
- **Ticket-volume trend** — monthly line chart with a 3-month moving average.
- **Category breakdown** — horizontal bar of ticket volume by category.
- **SLA view** — actual average resolution vs the SLA target per priority.
- **Channel mix** — donut chart of inbound channels.
- **Agent leaderboard** — ranked table with resolution time, breach rate, CSAT.
- **Sidebar filters** — date range, category, priority, and department, applied
  live across every chart.
- **"SQL behind this dashboard"** expander — shows the actual `.sql` powering
  the views, so the SQL is transparent, not hidden.

*Sample figures from a default run (seed = 42, ~8,000 tickets over 2022–2024):
**7,976** clean tickets, **91.8%** resolved, **9.9 h** average resolution,
**8.7%** SLA-breach rate, **4.78 / 5** average CSAT.*

---

## 🗂️ Project structure

```
data-pipeline-bi/
├── run_pipeline.py            # one-command entry point (→ etl.run)
├── requirements.txt
├── pytest.ini
├── README.md
├── etl/                       # the ETL package (one module per stage)
│   ├── config.py              # paths + business config (categories, SLAs…)
│   ├── generate_data.py       # synthetic, deliberately-messy ticket generator
│   ├── extract.py             # read raw CSV
│   ├── transform.py           # pandas: dedup, clean, validate, enrich
│   ├── load.py                # build star schema + load SQLite
│   └── run.py                 # orchestrator
├── sql/                       # schema DDL + analytical queries
│   ├── schema.sql
│   ├── kpi_summary.sql
│   ├── tickets_by_month.sql
│   ├── resolution_by_category.sql
│   ├── agent_leaderboard.sql
│   ├── sla_by_priority.sql
│   └── tickets_by_channel_department.sql
├── dashboard/
│   ├── app.py                 # Streamlit dashboard
│   └── queries.py             # SQL loader / data-access layer
├── tests/
│   └── test_transform.py      # 9 pytest cases on the transform logic
└── data/                      # generated at runtime (git-ignored)
    ├── raw/tickets_raw.csv
    ├── processed/tickets_clean.csv
    └── helpdesk.db
```

---

## 🧰 Tech stack

- **Python** — pandas, NumPy (ETL & data cleaning)
- **SQL / SQLite** — dimensional modelling, window functions, aggregation
- **Streamlit + Plotly** — interactive dashboard
- **pytest** — unit testing the transform logic
- Clean package layout, deterministic data generation, and git-ignored
  reproducible artefacts.

---

## 📚 What I learned / possible extensions

**What I learned**
- Designing a **star schema** and mapping natural keys to surrogate keys during
  the Load stage — the modelling mindset behind a real BI warehouse.
- Writing **window functions** (`RANK`, rolling `AVG`, share-of-total) in SQL
  rather than doing everything in pandas.
- Structuring an ETL project so each stage is **small, pure, and testable**,
  and building a synthetic dataset that's messy enough to make the cleaning
  meaningful.

**Extensions I'd add next**
- Swap SQLite for **PostgreSQL** and orchestrate with **Apache Airflow** or
  **dbt** for scheduled, incremental loads.
- Add a **data-quality report** (row counts, null rates, rejected-row log)
  emitted each run.
- Containerise with **Docker** and wire up **GitHub Actions** CI to run the
  pipeline + tests on every push.
- Add basic **forecasting** (e.g. ticket volume) to the dashboard.
