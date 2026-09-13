"""Customer-level feature engineering for RetailIQ."""

from __future__ import annotations

import numpy as np
import pandas as pd


# Features used by the K-Means segmentation model
SEGMENTATION_FEATURES = [
    "Recency",
    "Frequency",
    "Monetary",
]


# Features used for data-quality comparison and reporting
CUSTOMER_AUDIT_FEATURES = [
    "Recency",
    "Frequency",
    "Monetary",
    "GrossMonetary",
    "AverageOrderValue",
    "UnitsPurchased",
    "UniqueProducts",
    "CancellationRatePercent",
]


REQUIRED_COLUMNS = {
    "Invoice",
    "StockCode",
    "Quantity",
    "InvoiceDate",
    "Revenue",
    "CustomerID",
    "TransactionType",
    "IsExactReversalPair",
}


def _convert_boolean(series: pd.Series) -> pd.Series:
    """Convert Boolean or text Boolean values safely."""

    if pd.api.types.is_bool_dtype(series):
        return series.fillna(False).astype(bool)

    boolean_mapping = {
        "true": True,
        "false": False,
        "1": True,
        "0": False,
        "yes": True,
        "no": False,
    }

    return (
        series
        .astype("string")
        .str.strip()
        .str.lower()
        .map(boolean_mapping)
        .fillna(False)
        .astype(bool)
    )


def _prepare_customer_transactions(
    master_df: pd.DataFrame,
) -> pd.DataFrame:
    """Validate and standardise columns needed for customer features."""

    missing_columns = REQUIRED_COLUMNS.difference(
        master_df.columns
    )

    if missing_columns:
        raise KeyError(
            "Missing required customer-feature columns: "
            f"{sorted(missing_columns)}"
        )

    customer_transactions = master_df.copy()

    customer_transactions["CustomerID"] = pd.to_numeric(
        customer_transactions["CustomerID"],
        errors="coerce",
    ).astype("Int64")

    customer_transactions["InvoiceDate"] = pd.to_datetime(
        customer_transactions["InvoiceDate"],
        errors="coerce",
    )

    customer_transactions["Quantity"] = pd.to_numeric(
        customer_transactions["Quantity"],
        errors="coerce",
    )

    customer_transactions["Revenue"] = pd.to_numeric(
        customer_transactions["Revenue"],
        errors="coerce",
    )

    customer_transactions["Invoice"] = (
        customer_transactions["Invoice"]
        .astype("string")
        .str.strip()
    )

    customer_transactions["TransactionType"] = (
        customer_transactions["TransactionType"]
        .astype("string")
        .str.strip()
    )

    customer_transactions["IsExactReversalPair"] = (
        _convert_boolean(
            customer_transactions[
                "IsExactReversalPair"
            ]
        )
    )

    # Use the permanent normalised stock code when available.
    if "StockCodeNormalized" in customer_transactions.columns:
        customer_transactions["StockCodeNormalized"] = (
            customer_transactions["StockCodeNormalized"]
            .astype("string")
            .str.strip()
            .str.upper()
        )
    else:
        customer_transactions["StockCodeNormalized"] = (
            customer_transactions["StockCode"]
            .astype("string")
            .str.strip()
            .str.upper()
        )

    return customer_transactions


def build_customer_features(
    master_df: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Build RetailIQ customer features.

    Returns
    -------
    all_customer_features
        One row for every identified customer.

    customer_segmentation_features
        Customers with at least one valid sale after exact reversal
        transactions are excluded from modelling activity.
    """

    transactions = _prepare_customer_transactions(
        master_df
    )

    # Keep only rows with an identified customer.
    identified_history = transactions.loc[
        transactions["CustomerID"].notna()
    ].copy()

   # Customers with at least one valid positive sale before
# exact-reversal pairs are removed.
    complete_valid_sales = identified_history.loc[
    identified_history[
        "TransactionType"
    ].eq("Sale")
    & identified_history["Quantity"].gt(0)
    & identified_history["Revenue"].gt(0)
    & identified_history["InvoiceDate"].notna()
   ].copy()

    all_customer_ids = pd.Index(
    pd.array(
        complete_valid_sales[
            "CustomerID"
        ].drop_duplicates(),
        dtype="Int64",
    ),
    name="CustomerID",
    ).sort_values()

    # Exact reversal pairs are excluded from the monetary, purchase
    # and recency features used for customer segmentation.
    modelling_history = identified_history.loc[
        ~identified_history[
            "IsExactReversalPair"
        ]
    ].copy()

    valid_sales = modelling_history.loc[
        modelling_history[
            "TransactionType"
        ].eq("Sale")
        & modelling_history["Quantity"].gt(0)
        & modelling_history["Revenue"].gt(0)
        & modelling_history["InvoiceDate"].notna()
    ].copy()

    model_cancellations = modelling_history.loc[
        modelling_history[
            "TransactionType"
        ].eq("Cancellation")
    ].copy()

    if valid_sales.empty:
        raise ValueError(
            "No valid customer sales were found."
        )

    maximum_date = identified_history[
        "InvoiceDate"
    ].max()

    if pd.isna(maximum_date):
        raise ValueError(
            "InvoiceDate does not contain a valid date."
        )

    snapshot_date = (
        maximum_date.normalize()
        + pd.Timedelta(days=1)
    )

    customer_features = pd.DataFrame(
        index=all_customer_ids
    )

    # ---------------------------------------------------------
    # Recency
    # ---------------------------------------------------------

    last_sale_date = (
        valid_sales
        .groupby("CustomerID")["InvoiceDate"]
        .max()
        .dt.normalize()
    )

    customer_features["Recency"] = (
        snapshot_date - last_sale_date
    ).dt.days.reindex(all_customer_ids)

    # ---------------------------------------------------------
    # Frequency and gross monetary value
    # ---------------------------------------------------------

    sales_summary = (
        valid_sales
        .groupby("CustomerID")
        .agg(
            Frequency=("Invoice", "nunique"),
            GrossMonetary=("Revenue", "sum"),
            UnitsPurchased=("Quantity", "sum"),
            UniqueProducts=(
                "StockCodeNormalized",
                "nunique",
            ),
        )
    )

    for column in [
        "Frequency",
        "GrossMonetary",
        "UnitsPurchased",
        "UniqueProducts",
    ]:
        customer_features[column] = (
            sales_summary[column]
            .reindex(
                all_customer_ids,
                fill_value=0,
            )
        )

    # ---------------------------------------------------------
    # Net monetary value
    # ---------------------------------------------------------

    cancellation_revenue = (
        model_cancellations
        .groupby("CustomerID")["Revenue"]
        .sum()
        .reindex(
            all_customer_ids,
            fill_value=0,
        )
    )

    customer_features["Monetary"] = (
        customer_features["GrossMonetary"]
        + cancellation_revenue
    )

    # ---------------------------------------------------------
    # Average order value
    # ---------------------------------------------------------

    customer_features["AverageOrderValue"] = (
        customer_features["GrossMonetary"]
        .div(
            customer_features[
                "Frequency"
            ].replace(0, np.nan)
        )
        .fillna(0)
    )

        # ---------------------------------------------------------
    # Cancellation rate
    # ---------------------------------------------------------
    # Numerator:
    # All distinct cancellation invoices, including exact
    # reversal-pair cancellations.
    #
    # Denominator:
    # Valid sale frequency after reversal removal
    # + all distinct cancellation invoices.

    complete_cancellation_history = (
        identified_history.loc[
            identified_history[
                "TransactionType"
            ].eq("Cancellation"),
            [
                "CustomerID",
                "Invoice",
            ],
        ]
        .drop_duplicates()
    )

    cancellation_invoices = (
        complete_cancellation_history
        .groupby("CustomerID")["Invoice"]
        .nunique()
        .reindex(
            all_customer_ids,
            fill_value=0,
        )
        .astype(float)
    )

    total_customer_orders = (
        customer_features[
            "Frequency"
        ].astype(float)
        + cancellation_invoices
    )

    customer_features[
        "CancellationRatePercent"
    ] = (
        cancellation_invoices
        .div(
            total_customer_orders.replace(
                0,
                np.nan,
            )
        )
        .mul(100)
        .fillna(0)
    )

    # Arrange the output consistently.
    customer_features = customer_features[
        CUSTOMER_AUDIT_FEATURES
    ].sort_index()

    # Customers are eligible only if they retain at least one
    # valid sale after exact reversal pairs are removed.
    eligible_customer_ids = pd.Index(
        pd.array(
            valid_sales[
                "CustomerID"
            ].drop_duplicates(),
            dtype="Int64",
        ),
        name="CustomerID",
    ).sort_values()

    customer_segmentation_features = (
        customer_features.loc[
            eligible_customer_ids
        ]
        .copy()
        .sort_index()
    )

    # Final validation
    model_matrix = (
        customer_segmentation_features[
            SEGMENTATION_FEATURES
        ]
        .to_numpy(dtype=float)
    )

    if not np.isfinite(model_matrix).all():
        raise ValueError(
            "Segmentation features contain missing "
            "or infinite values."
        )

    return (
        customer_features,
        customer_segmentation_features,
    )