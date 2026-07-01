-- Agent performance leaderboard.
-- Ranks agents by resolved volume using the RANK() window function, alongside
-- their average resolution time, SLA-breach rate and CSAT. Great example of a
-- window function combined with multi-table joins and conditional aggregation.
SELECT
    RANK() OVER (ORDER BY SUM(f.is_resolved) DESC)      AS rank,
    a.agent_name,
    COUNT(*)                                            AS assigned_tickets,
    SUM(f.is_resolved)                                  AS resolved_tickets,
    ROUND(AVG(f.resolution_hours), 1)                   AS avg_resolution_hours,
    ROUND(100.0 * SUM(f.sla_breached)
          / NULLIF(SUM(f.is_resolved), 0), 1)           AS sla_breach_pct,
    ROUND(AVG(f.satisfaction_score), 2)                 AS avg_satisfaction
FROM fact_tickets AS f
JOIN dim_agent    AS a ON f.agent_key = a.agent_key
GROUP BY a.agent_name
ORDER BY resolved_tickets DESC;
