from pathlib import Path

import numpy as np
import pandas as pd

from src.config import (
    EDA_OUTPUT_DIR,
    MASTER_DATA_PATH
)


REQUIRED_MASTER_COLUMNS = {
    "Invoice",
    "StockCode",
    "StockCodeNormalized",
    "Description",
    "Quantity",
    "InvoiceDate",
    "Price",
    "CustomerID",
    "Country",
    "Revenue",
    "IsCancelled",
    "TransactionType"
}


ALLOWED_TRANSACTION_TYPES = {
    "Sale",
    "Cancellation",
    "Postage and Carrier charges",
    "Operational Adjustment",
    "Other",
    "Manual",
    "Discount",
    "Bank Charges",
    "Financial Adjustment",
    "Commission charges",
    "Test Transaction",
    "Bad Debt"
}


def validate_master_data(
    master_df: pd.DataFrame
) -> pd.Series:
    """Validate the cleaned RetailIQ master dataset."""

    missing_columns = (
        REQUIRED_MASTER_COLUMNS
        - set(master_df.columns)
    )

    if missing_columns:
        raise ValueError(
            "Missing required columns: "
            f"{sorted(missing_columns)}"
        )

    expected_revenue = (
        master_df["Quantity"]
        * master_df["Price"]
    )

    revenue_matches = np.isclose(
        master_df["Revenue"],
        expected_revenue,
        equal_nan=True
    )

    unexpected_types = set(
        master_df["TransactionType"]
        .dropna()
        .unique()
    ) - ALLOWED_TRANSACTION_TYPES

    validation_results = pd.Series({
        "Rows": len(master_df),
        "Columns": master_df.shape[1],
        "DuplicateRows": (
            master_df.duplicated().sum()
        ),
        "MissingInvoiceDates": (
            master_df["InvoiceDate"]
            .isna()
            .sum()
        ),
        "RevenueMismatches": (
            ~revenue_matches
        ).sum(),
        "UnexpectedTransactionTypes": (
            len(unexpected_types)
        )
    })

    critical_failures = {
        "DuplicateRows":
            validation_results["DuplicateRows"],

        "MissingInvoiceDates":
            validation_results["MissingInvoiceDates"],

        "RevenueMismatches":
            validation_results["RevenueMismatches"],

        "UnexpectedTransactionTypes":
            validation_results[
                "UnexpectedTransactionTypes"
            ]
    }

    failed_checks = {
        name: value
        for name, value in critical_failures.items()
        if value != 0
    }

    if failed_checks:
        raise ValueError(
            "Master-data validation failed: "
            f"{failed_checks}. "
            f"Unexpected types: {unexpected_types}"
        )

    return validation_results


def load_clean_master(
    file_path: Path | str = MASTER_DATA_PATH,
    validate: bool = True
) -> pd.DataFrame:
    """Load and optionally validate the cleaned master data."""

    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(
            f"Cleaned master dataset not found: "
            f"{file_path}"
        )

    master_df = pd.read_csv(
        file_path,
        compression="infer",
        low_memory=False
    )

    master_df["InvoiceDate"] = pd.to_datetime(
        master_df["InvoiceDate"],
        errors="raise"
    )

    text_columns = [
        "Invoice",
        "StockCode",
        "StockCodeNormalized",
        "Description",
        "Country",
        "TransactionType"
    ]

    for column in text_columns:
        if column in master_df.columns:
            master_df[column] = (
                master_df[column].astype("string")
            )

    numeric_columns = [
        "Quantity",
        "Price",
        "Revenue"
    ]

    for column in numeric_columns:
        master_df[column] = pd.to_numeric(
            master_df[column],
            errors="raise"
        )

    master_df["CustomerID"] = pd.to_numeric(
        master_df["CustomerID"],
        errors="coerce"
    ).astype("Int64")

    if validate:
        validate_master_data(master_df)

    return master_df


def create_sales_view(
    master_df: pd.DataFrame
) -> pd.DataFrame:
    """Return valid positive product-sale lines."""

    sale_mask = (
        master_df["TransactionType"].eq("Sale")
        & master_df["Quantity"].gt(0)
        & master_df["Price"].gt(0)
        & master_df["Revenue"].gt(0)
    )

    return master_df.loc[sale_mask].copy()


def create_customer_sales_view(
    sales_df: pd.DataFrame
) -> pd.DataFrame:
    """Return sale lines suitable for customer modelling."""

    return sales_df.loc[
        sales_df["CustomerID"].notna()
    ].copy()


def create_financial_activity_view(
    master_df: pd.DataFrame
) -> pd.DataFrame:
    """Return cancellations, charges and adjustments."""

    return master_df.loc[
        ~master_df["TransactionType"].eq("Sale")
    ].copy()


def load_eda_table(
    filename: str,
    index_col=None
) -> pd.DataFrame:
    """Load an exported EDA table."""

    safe_filename = Path(filename).name

    if safe_filename != filename:
        raise ValueError(
            "Pass a filename only, not a directory path."
        )

    table_path = EDA_OUTPUT_DIR / safe_filename

    if not table_path.exists():
        raise FileNotFoundError(
            f"EDA table not found: {table_path}"
        )

    return pd.read_csv(
        table_path,
        index_col=index_col
    )