-- Resolution performance broken down by category.
-- Shows volume, average/median-ish resolution time and SLA-breach rate per
-- category so the dashboard can highlight the most painful support areas.
SELECT
    c.category_name,
    COUNT(*)                                            AS ticket_count,
    ROUND(AVG(f.resolution_hours), 1)                   AS avg_resolution_hours,
    ROUND(100.0 * SUM(f.sla_breached)
          / NULLIF(SUM(f.is_resolved), 0), 1)           AS sla_breach_pct,
    ROUND(AVG(f.satisfaction_score), 2)                 AS avg_satisfaction
FROM fact_tickets  AS f
JOIN dim_category  AS c ON f.category_key = c.category_key
GROUP BY c.category_name
ORDER BY ticket_count DESC;
