-- Monthly ticket-volume trend with a 3-month moving average.
-- Demonstrates a JOIN to dim_date plus a window function (AVG OVER a rolling
-- frame) to smooth the trend line shown on the dashboard.
SELECT
    d.month_start,
    d.month_name,
    COUNT(*)                                       AS ticket_count,
    SUM(f.sla_breached)                            AS sla_breaches,
    ROUND(
        AVG(COUNT(*)) OVER (
            ORDER BY d.month_start
            ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
        ),
        0
    )                                              AS ticket_count_3mo_avg
FROM fact_tickets AS f
JOIN dim_date     AS d ON f.date_key = d.date_key
GROUP BY d.month_start, d.month_name
ORDER BY d.month_start;
