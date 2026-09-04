## Original Dataset Variables

| Column | Description |
|---|---|
| Invoice | Unique invoice/transaction number |
| StockCode | Unique product code |
| Description | Product description |
| Quantity | Number of units in the transaction |
| InvoiceDate | Date and time of the transaction |
| Price | Price per unit |
| Customer ID | Unique customer identifier |
| Country | Customer's country |

## Engineered Variables

| Column | Description |
|---|---|
| Revenue | Quantity multiplied by Price |
| IsCancelled | Indicates whether an invoice is a cancellation |

## Variables Planned During Data Cleaning

The following variables will be created later:
| Column | Description |
|---|---|
| IsNegativeQuantity | Indicates Quantity below zero |
| IsNegativePrice | Indicates Price below zero |
| IsZeroPrice | Indicates Price equal to zero |
| HasCustomerID | Indicates whether Customer ID is available |
| TransactionType | Business classification of the transaction |

## Transaction Types

- Sale
- Cancellation
- Operational Adjustment
- Financial Adjustment
- Bad debt
- Test transaction
- Manual
- Other
