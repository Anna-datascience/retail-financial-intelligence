# RetailIQ Business Rules

## Purpose

This document defines how transactions in the RetailIQ dataset will be interpreted during data cleaning and analysis.

The raw dataset will always be preserved. Transactions will be classified according to their business meaning instead of automatically deleting unusual or negative values.

## Transaction Classification Rules

### 1. Sale

A transaction is classified as a Sale when:

- Quantity > 0
- Price > 0
- Invoice does not start with "C"

These transactions represent normal customer purchases.

### 2. Cancellation

A transaction is classified as a Cancellation when:

- Invoice starts with "C"

Cancellation transactions generally have negative quantities and represent returned or cancelled purchases.

### 3. Financial Adjustment

A transaction is classified as a Financial Adjustment when:

- Price < 0
- Invoice does not start with "C"

Examples identified during data understanding include "Adjust bad debt".

These records will not be treated as normal product sales.

### 4. Operational Adjustment

A transaction is classified as an Operational Adjustment when:

- Quantity < 0
- Invoice does not start with "C"

Examples identified during data understanding include:

- damaged
- lost
- short
- wet
- mixed stock
- inventory corrections

These transactions may represent inventory or operational adjustments rather than customer purchases.

### 5. Other

Transactions that do not satisfy the rules above will be classified as Other.

Examples may include:

- zero-price transactions
- zero-quantity transactions
- unusual administrative records

These records will be investigated before deciding whether they should be included in a particular analysis.

## Missing Customer IDs

Transactions with missing Customer ID will not automatically be deleted.

They may still contain useful information for:

- Revenue analysis
- Sales forecasting
- Product analysis
- Anomaly detection

Customer ID will be required for customer-level analysis such as RFM analysis and K-Means customer segmentation.

## Duplicate Transactions

Exact duplicate rows will be removed from the cleaned analytical dataset.

The original raw dataset will remain unchanged.

## Anomaly Detection

Unusual transactions will not automatically be considered fraud.

RetailIQ will identify unusual financial and transactional behaviour using:

1. Business rules
2. Isolation Forest anomaly detection

Anomalies will be reviewed according to their business context.

## Forecasting

Revenue forecasting will focus on transactions appropriate for measuring actual sales performance.

Cancellations, financial adjustments and operational adjustments will be analysed separately before determining their treatment in the forecasting dataset.

## Core Principle

RetailIQ will preserve the financial meaning of transactions rather than blindly removing unusual observations as data errors.