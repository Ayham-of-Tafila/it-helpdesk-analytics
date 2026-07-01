-- SLA compliance by priority tier.
-- Compares each priority's SLA target against actual performance and computes
-- the share of that priority's total volume (window SUM over all rows).
SELECT
    p.priority_name,
    p.sla_target_hours,
    COUNT(*)                                            AS ticket_count,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1)  AS pct_of_all_tickets,
    ROUND(AVG(f.resolution_hours), 1)                   AS avg_resolution_hours,
    SUM(f.sla_breached)                                 AS sla_breaches,
    ROUND(100.0 * SUM(f.sla_breached)
          / NULLIF(SUM(f.is_resolved), 0), 1)           AS sla_breach_pct
FROM fact_tickets  AS f
JOIN dim_priority  AS p ON f.priority_key = p.priority_key
GROUP BY p.priority_name, p.sla_target_hours
ORDER BY p.sla_target_hours;
