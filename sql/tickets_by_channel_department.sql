-- Inbound-channel and department breakdown.
-- Used by the dashboard's category/channel pie and department bar charts.
SELECT
    channel,
    department,
    COUNT(*)                          AS ticket_count,
    ROUND(AVG(resolution_hours), 1)   AS avg_resolution_hours
FROM fact_tickets
GROUP BY channel, department
ORDER BY ticket_count DESC;
