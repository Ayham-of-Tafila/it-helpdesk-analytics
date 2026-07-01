-- KPI headline numbers for the dashboard's top row.
-- A single-row summary: total tickets, resolution rate, median resolution
-- time, SLA-breach rate, and average satisfaction.
SELECT
    COUNT(*)                                            AS total_tickets,
    SUM(is_resolved)                                    AS resolved_tickets,
    ROUND(100.0 * SUM(is_resolved) / COUNT(*), 1)       AS resolved_pct,
    ROUND(AVG(resolution_hours), 1)                     AS avg_resolution_hours,
    ROUND(100.0 * SUM(sla_breached) / NULLIF(SUM(is_resolved), 0), 1)
                                                        AS sla_breach_pct,
    ROUND(AVG(satisfaction_score), 2)                   AS avg_satisfaction
FROM fact_tickets;
