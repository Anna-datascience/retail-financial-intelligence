-- RetailIQ analytical layer (PostgreSQL 14+)
-- Star-style schema built from data/processed/retailiq_cleaned_master.csv.gz
-- Run:  psql -d retailiq -f sql/schema.sql
-- Load: see sql/load_data.sql

DROP SCHEMA IF EXISTS retailiq CASCADE;
CREATE SCHEMA retailiq;
SET search_path = retailiq;

-- 1) Staging: one row per cleaned transaction line (exactly the master file columns)
CREATE TABLE stg_transactions (
    invoice               TEXT,
    stock_code            TEXT,
    stock_code_normalized TEXT,
    description           TEXT,
    quantity              INTEGER,
    invoice_date          TIMESTAMP,
    price                 NUMERIC(12,4),
    customer_id           NUMERIC(14,1),     -- may arrive as 12345.0 in the CSV; cast to BIGINT later
    country               TEXT,
    revenue               NUMERIC(14,4),
    is_cancelled          BOOLEAN,
    transaction_type      TEXT
);

-- 2) Dimensions
CREATE TABLE dim_date (
    date_key     DATE PRIMARY KEY,
    year         SMALLINT NOT NULL,
    quarter      SMALLINT NOT NULL,
    month        SMALLINT NOT NULL,
    month_start  DATE     NOT NULL,
    iso_week     SMALLINT NOT NULL,
    weekday      SMALLINT NOT NULL,        -- 1 = Monday ... 7 = Sunday
    weekday_name TEXT     NOT NULL
);

CREATE TABLE dim_customer (
    customer_id BIGINT PRIMARY KEY,
    country     TEXT,                      -- most recent country seen for the customer
    first_order_date DATE,
    last_order_date  DATE
);

CREATE TABLE dim_product (
    stock_code_normalized TEXT PRIMARY KEY,
    description           TEXT
);

-- 3) Fact table: every cleaned line, classified by transaction_type
CREATE TABLE fact_transactions (
    transaction_id        BIGSERIAL PRIMARY KEY,
    invoice               TEXT      NOT NULL,
    invoice_ts            TIMESTAMP NOT NULL,
    date_key              DATE      NOT NULL REFERENCES dim_date (date_key),
    customer_id           BIGINT    REFERENCES dim_customer (customer_id),   -- NULL = no customer ID
    stock_code_normalized TEXT      REFERENCES dim_product (stock_code_normalized),
    country               TEXT,
    quantity              INTEGER   NOT NULL,
    unit_price            NUMERIC(12,4) NOT NULL,
    revenue               NUMERIC(14,4) NOT NULL,   -- quantity x unit_price (GBP)
    is_cancelled          BOOLEAN   NOT NULL,
    transaction_type      TEXT      NOT NULL
        CHECK (transaction_type IN (
            'Sale','Cancellation','Postage and Carrier charges','Operational Adjustment',
            'Other','Manual','Discount','Bank Charges','Financial Adjustment',
            'Commission charges','Test Transaction','Bad Debt'))
);

CREATE INDEX ix_fact_date     ON fact_transactions (date_key);
CREATE INDEX ix_fact_customer ON fact_transactions (customer_id);
CREATE INDEX ix_fact_product  ON fact_transactions (stock_code_normalized);
CREATE INDEX ix_fact_invoice  ON fact_transactions (invoice);
CREATE INDEX ix_fact_type     ON fact_transactions (transaction_type);

-- 4) Model outputs (loaded from the committed CSV artifacts)
CREATE TABLE customer_segment_names (
    cluster      SMALLINT PRIMARY KEY,
    cluster_name TEXT NOT NULL
);

CREATE TABLE customer_segments (
    customer_id BIGINT PRIMARY KEY,
    cluster     SMALLINT NOT NULL REFERENCES customer_segment_names (cluster)
);

CREATE TABLE anomaly_invoice_cases (
    case_id                 TEXT PRIMARY KEY,
    invoice                 TEXT,
    invoice_date            TIMESTAMP,
    highest_alert_priority  SMALLINT,      -- 1 = P1 (review immediately) ... 3 = P3 (monitor)
    case_priority           TEXT,
    primary_alert_category  TEXT,
    alert_revenue           NUMERIC(14,4),
    business_owner          TEXT,
    recommended_action      TEXT,
    review_status           TEXT
);

CREATE TABLE forecast_test_predictions (
    forecast_date DATE PRIMARY KEY,
    actual_revenue    NUMERIC(14,2),
    predicted_revenue NUMERIC(14,2)
);

CREATE TABLE future_revenue_forecast (
    forecast_date          DATE PRIMARY KEY,
    forecast_horizon_day   SMALLINT,
    predicted_revenue      NUMERIC(14,2),
    model                  TEXT,
    lower_revenue_estimate NUMERIC(14,2),
    upper_revenue_estimate NUMERIC(14,2)
);

-- 5) Convenience views
CREATE VIEW v_sales AS
SELECT * FROM fact_transactions
WHERE transaction_type = 'Sale' AND quantity > 0 AND unit_price > 0 AND revenue > 0;

CREATE VIEW v_financial_activity AS
SELECT * FROM fact_transactions
WHERE transaction_type <> 'Sale';
