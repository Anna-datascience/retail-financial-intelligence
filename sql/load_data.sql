-- Load the cleaned master file into the star schema.
-- 1) Create a plain CSV from the gzip file first (PowerShell / bash):
--      python -c "import pandas as pd; pd.read_csv('data/processed/retailiq_cleaned_master.csv.gz').to_csv('data/processed/master.csv', index=False)"
-- 2) Run from psql (the \copy command reads the file on your own machine):
SET search_path = retailiq;

TRUNCATE stg_transactions;
\copy stg_transactions (invoice, stock_code, stock_code_normalized, description, quantity, invoice_date, price, customer_id, country, revenue, is_cancelled, transaction_type) FROM 'data/processed/master.csv' WITH (FORMAT csv, HEADER true)
-- NOTE: the column order above must match the CSV header order. Check it with:  head -1 data/processed/master.csv

-- Dimensions
INSERT INTO dim_date
SELECT d::date,
       EXTRACT(YEAR FROM d), EXTRACT(QUARTER FROM d), EXTRACT(MONTH FROM d),
       date_trunc('month', d)::date, EXTRACT(WEEK FROM d), EXTRACT(ISODOW FROM d), to_char(d, 'Dy')
FROM generate_series('2009-12-01'::date, '2011-12-31'::date, interval '1 day') AS g(d);

INSERT INTO dim_product
SELECT stock_code_normalized,
       (array_agg(description ORDER BY invoice_date DESC) FILTER (WHERE description IS NOT NULL))[1]
FROM stg_transactions
WHERE stock_code_normalized IS NOT NULL
GROUP BY stock_code_normalized;

INSERT INTO dim_customer
SELECT customer_id::BIGINT,
       (array_agg(country ORDER BY invoice_date DESC))[1],
       MIN(invoice_date)::date, MAX(invoice_date)::date
FROM stg_transactions
WHERE customer_id IS NOT NULL
GROUP BY customer_id::BIGINT;

-- Fact
INSERT INTO fact_transactions
    (invoice, invoice_ts, date_key, customer_id, stock_code_normalized, country,
     quantity, unit_price, revenue, is_cancelled, transaction_type)
SELECT invoice, invoice_date, invoice_date::date, customer_id::BIGINT, stock_code_normalized, country,
       quantity, price, revenue, is_cancelled, transaction_type
FROM stg_transactions;

-- Model outputs: use \copy with the committed CSV files
INSERT INTO customer_segment_names VALUES (0,'Inactive / Low Frequency'), (1,'Active Core'), (2,'VIP / Strategic');

\copy customer_segments (customer_id, cluster) FROM 'customer_segments_two_columns.csv' WITH (FORMAT csv, HEADER true)
-- Create that two-column file with:
--   python -c "import pandas as pd; d=pd.read_csv('data/processed/customer_segments.csv.gz'); d[['CustomerID','Cluster']].astype({'CustomerID':'int64'}).to_csv('customer_segments_two_columns.csv', index=False)"

\copy future_revenue_forecast (forecast_date, forecast_horizon_day, predicted_revenue, model, lower_revenue_estimate, upper_revenue_estimate) FROM 'reports/tables/future_30_day_revenue_forecast.csv' WITH (FORMAT csv, HEADER true)

ANALYZE;
