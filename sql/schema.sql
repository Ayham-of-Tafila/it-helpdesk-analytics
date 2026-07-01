-- ---------------------------------------------------------------------------
-- IT Helpdesk Analytics — star-schema DDL
--
-- One fact table (fact_tickets) surrounded by four conformed dimensions.
-- Executed by etl/load.py via sqlite3.executescript() on every pipeline run.
-- ---------------------------------------------------------------------------

DROP TABLE IF EXISTS fact_tickets;
DROP TABLE IF EXISTS dim_date;
DROP TABLE IF EXISTS dim_category;
DROP TABLE IF EXISTS dim_priority;
DROP TABLE IF EXISTS dim_agent;

-- --- Dimension: date -------------------------------------------------------
CREATE TABLE dim_date (
    date_key     INTEGER PRIMARY KEY,
    full_date    TEXT    NOT NULL UNIQUE,   -- 'YYYY-MM-DD'
    month_start  TEXT    NOT NULL,          -- first day of the month
    month_name   TEXT    NOT NULL,          -- e.g. 'Mar 2023'
    year         INTEGER NOT NULL,
    month        INTEGER NOT NULL,
    day_of_week  TEXT    NOT NULL
);

-- --- Dimension: category ---------------------------------------------------
CREATE TABLE dim_category (
    category_key  INTEGER PRIMARY KEY,
    category_name TEXT    NOT NULL UNIQUE
);

-- --- Dimension: priority (carries the SLA target as an attribute) ----------
CREATE TABLE dim_priority (
    priority_key     INTEGER PRIMARY KEY,
    priority_name    TEXT    NOT NULL UNIQUE,
    sla_target_hours INTEGER NOT NULL
);

-- --- Dimension: agent ------------------------------------------------------
CREATE TABLE dim_agent (
    agent_key  INTEGER PRIMARY KEY,
    agent_name TEXT    NOT NULL UNIQUE
);

-- --- Fact: one row per support ticket --------------------------------------
CREATE TABLE fact_tickets (
    ticket_id          TEXT PRIMARY KEY,
    date_key           INTEGER NOT NULL,
    category_key       INTEGER NOT NULL,
    priority_key       INTEGER NOT NULL,
    agent_key          INTEGER NOT NULL,
    created_at         TEXT    NOT NULL,
    resolved_at        TEXT,                 -- NULL while a ticket is open
    channel            TEXT,
    department         TEXT,
    created_hour       INTEGER,
    is_resolved        INTEGER NOT NULL,     -- 0/1 boolean
    resolution_hours   REAL,                 -- NULL while a ticket is open
    sla_breached       INTEGER NOT NULL,     -- 0/1 boolean
    satisfaction_score REAL,                 -- 1..5, NULL if not resolved
    FOREIGN KEY (date_key)     REFERENCES dim_date (date_key),
    FOREIGN KEY (category_key) REFERENCES dim_category (category_key),
    FOREIGN KEY (priority_key) REFERENCES dim_priority (priority_key),
    FOREIGN KEY (agent_key)    REFERENCES dim_agent (agent_key)
);

-- Indexes on the foreign keys keep the dashboard's group-by queries fast.
CREATE INDEX idx_fact_date     ON fact_tickets (date_key);
CREATE INDEX idx_fact_category ON fact_tickets (category_key);
CREATE INDEX idx_fact_priority ON fact_tickets (priority_key);
CREATE INDEX idx_fact_agent    ON fact_tickets (agent_key);
