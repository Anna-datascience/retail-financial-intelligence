-- RetailIQ business queries (PostgreSQL). Run after schema.sql and load_data.sql.
SET search_path = retailiq;

-- Q1. Monthly revenue with month-over-month growth (complete months only)
WITH monthly AS (
    SELECT d.month_start, SUM(s.revenue) AS revenue, COUNT(DISTINCT s.invoice) AS orders
    FROM v_sales s JOIN dim_date d USING (date_key)
    GROUP BY d.month_start
)
SELECT month_start,
       ROUND(revenue, 0) AS revenue_gbp,
       orders,
       ROUND(100.0 * (revenue - LAG(revenue) OVER (ORDER BY month_start))
             / NULLIF(LAG(revenue) OVER (ORDER BY month_start), 0), 1) AS mom_growth_pct
FROM monthly
WHERE month_start < '2011-12-01'
ORDER BY month_start;

-- Q2. Top 10 customers by revenue and their share of total
WITH cust AS (
    SELECT customer_id, SUM(revenue) AS revenue, COUNT(DISTINCT invoice) AS orders
    FROM v_sales WHERE customer_id IS NOT NULL GROUP BY customer_id
)
SELECT customer_id, ROUND(revenue, 0) AS revenue_gbp, orders,
       ROUND(100.0 * revenue / SUM(revenue) OVER (), 2) AS share_pct
FROM cust ORDER BY revenue DESC LIMIT 10;

-- Q3. Revenue by country (top 10) with share
SELECT country, ROUND(SUM(revenue), 0) AS revenue_gbp,
       ROUND(100.0 * SUM(revenue) / SUM(SUM(revenue)) OVER (), 1) AS share_pct
FROM v_sales GROUP BY country ORDER BY revenue_gbp DESC LIMIT 10;

-- Q4. Cancellation rate by month (value of cancellations relative to sales)
SELECT d.month_start,
       ROUND(SUM(revenue) FILTER (WHERE transaction_type = 'Sale'), 0)               AS sales_gbp,
       ROUND(-SUM(revenue) FILTER (WHERE transaction_type = 'Cancellation'), 0)      AS cancelled_gbp,
       ROUND(100.0 * -SUM(revenue) FILTER (WHERE transaction_type = 'Cancellation')
             / NULLIF(SUM(revenue) FILTER (WHERE transaction_type = 'Sale'), 0), 1)  AS cancellation_rate_pct
FROM fact_transactions f JOIN dim_date d USING (date_key)
GROUP BY d.month_start ORDER BY d.month_start;

-- Q5. ABC product classification (A = first 80 % of revenue, B = next 15 %, C = last 5 %)
WITH prod AS (
    SELECT stock_code_normalized, SUM(revenue) AS revenue
    FROM v_sales GROUP BY stock_code_normalized
), ranked AS (
    SELECT *, SUM(revenue) OVER (ORDER BY revenue DESC) / SUM(revenue) OVER () AS cum_share
    FROM prod
)
SELECT CASE WHEN cum_share <= 0.80 THEN 'A' WHEN cum_share <= 0.95 THEN 'B' ELSE 'C' END AS abc_class,
       COUNT(*) AS products, ROUND(SUM(revenue), 0) AS revenue_gbp
FROM ranked GROUP BY 1 ORDER BY 1;

-- Q6. RFM scores per customer (reference date = day after the last sale)
WITH ref AS (SELECT MAX(date_key) + 1 AS ref_date FROM v_sales),
rfm AS (
    SELECT s.customer_id,
           (SELECT ref_date FROM ref) - MAX(s.date_key) AS recency_days,
           COUNT(DISTINCT s.invoice) AS frequency,
           SUM(s.revenue)            AS monetary
    FROM v_sales s WHERE s.customer_id IS NOT NULL GROUP BY s.customer_id
)
SELECT customer_id, recency_days, frequency, ROUND(monetary, 0) AS monetary_gbp,
       NTILE(5) OVER (ORDER BY recency_days DESC) AS r_score,
       NTILE(5) OVER (ORDER BY frequency)         AS f_score,
       NTILE(5) OVER (ORDER BY monetary)          AS m_score
FROM rfm ORDER BY monetary DESC LIMIT 20;

-- Q7. Cohort retention: share of each first-purchase month cohort that orders again in later months
WITH first_order AS (
    SELECT customer_id, date_trunc('month', MIN(date_key))::date AS cohort_month
    FROM v_sales WHERE customer_id IS NOT NULL GROUP BY customer_id
), activity AS (
    SELECT DISTINCT s.customer_id, date_trunc('month', s.date_key)::date AS active_month
    FROM v_sales s WHERE s.customer_id IS NOT NULL
)
SELECT f.cohort_month,
       (EXTRACT(YEAR FROM age(a.active_month, f.cohort_month)) * 12
        + EXTRACT(MONTH FROM age(a.active_month, f.cohort_month)))::int AS months_since_first,
       COUNT(*) AS active_customers,
       ROUND(100.0 * COUNT(*) / MAX(COUNT(*)) FILTER (WHERE a.active_month = f.cohort_month)
             OVER (PARTITION BY f.cohort_month), 1) AS retention_pct
FROM first_order f JOIN activity a USING (customer_id)
GROUP BY f.cohort_month, a.active_month
ORDER BY f.cohort_month, months_since_first;

-- Q8. Segment business profile (customers, revenue and revenue share per segment)
SELECT n.cluster_name,
       COUNT(DISTINCT cs.customer_id)                                   AS customers,
       ROUND(SUM(s.revenue), 0)                                         AS revenue_gbp,
       ROUND(100.0 * SUM(s.revenue) / SUM(SUM(s.revenue)) OVER (), 1)   AS revenue_share_pct
FROM customer_segments cs
JOIN customer_segment_names n USING (cluster)
JOIN v_sales s USING (customer_id)
GROUP BY n.cluster_name ORDER BY revenue_gbp DESC;

-- Q9. Finance control check: invoices with revenue that does not equal quantity x price
SELECT invoice, COUNT(*) AS lines, ROUND(SUM(ABS(revenue - quantity * unit_price)), 2) AS difference_gbp
FROM fact_transactions
GROUP BY invoice
HAVING SUM(ABS(revenue - quantity * unit_price)) > 0.01
ORDER BY difference_gbp DESC LIMIT 20;

-- Q10. Reconciliation of transaction types: line count and net amount by type
SELECT transaction_type, COUNT(*) AS lines, ROUND(SUM(revenue), 0) AS net_amount_gbp
FROM fact_transactions GROUP BY transaction_type ORDER BY net_amount_gbp DESC;

-- Q11. Anomaly review queue by priority and owner (needs anomaly_invoice_cases loaded)
SELECT highest_alert_priority AS priority, business_owner, COUNT(*) AS cases,
       ROUND(SUM(alert_revenue), 0) AS alert_revenue_gbp
FROM anomaly_invoice_cases
GROUP BY 1, 2 ORDER BY 1, cases DESC;

-- Q12. 30-day forecast summary for the next period
SELECT MIN(forecast_date) AS from_date, MAX(forecast_date) AS to_date,
       ROUND(SUM(predicted_revenue), 0)        AS total_forecast_gbp,
       ROUND(SUM(lower_revenue_estimate), 0)   AS lower_gbp,
       ROUND(SUM(upper_revenue_estimate), 0)   AS upper_gbp
FROM future_revenue_forecast;
