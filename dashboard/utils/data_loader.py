"""Cached data loaders for the RetailIQ dashboard."""

from __future__ import annotations

import json
from pathlib import Path

import joblib
import pandas as pd
import streamlit as st


PROJECT_ROOT = (
    Path(__file__)
    .resolve()
    .parents[2]
)

PROCESSED_DATA_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
)

MODELS_DIR = (
    PROJECT_ROOT
    / "models"
)

REPORT_TABLES_DIR = (
    PROJECT_ROOT
    / "reports"
    / "tables"
)

REPORT_METRICS_DIR = (
    PROJECT_ROOT
    / "reports"
    / "metrics"
)

EDA_DATA_DIR = (
    PROCESSED_DATA_DIR
    / "eda"
)

MARKET_BASKET_DATA_DIR = (
    PROCESSED_DATA_DIR
    / "market_basket"
)

ANOMALY_DATA_DIR = (
    PROCESSED_DATA_DIR
    / "anomaly_detection"
)

ANOMALY_MODELS_DIR = (
    MODELS_DIR
    / "anomaly_detection"
)


FORECAST_COMPARISON_FILE = (
    REPORT_TABLES_DIR
    / "forecast_model_comparison.csv"
)

FORECAST_TEST_PREDICTIONS_FILE = (
    REPORT_TABLES_DIR
    / "forecast_test_predictions.csv"
)

FUTURE_REVENUE_FORECAST_FILE = (
    REPORT_TABLES_DIR
    / "future_30_day_revenue_forecast.csv"
)

FORECAST_METADATA_FILE = (
    MODELS_DIR
    / "forecast_metadata.json"
)

REVENUE_FORECAST_FIGURES_DIR = (
    PROJECT_ROOT
    / "reports"
    / "figures"
    / "revenue_forecasting"
)

FORECAST_TEST_FIGURE_FILE = (
    REVENUE_FORECAST_FIGURES_DIR
    / "forecast_test_comparison.png"
)

FORECAST_MODEL_WAPE_FIGURE_FILE = (
    REVENUE_FORECAST_FIGURES_DIR
    / "forecast_model_wape_comparison.png"
)

FUTURE_FORECAST_FIGURE_FILE = (
    REVENUE_FORECAST_FIGURES_DIR
    / "future_30_day_revenue_forecast.png"
)



def require_file(file_path: Path) -> Path:
    """Raise a clear error when an artifact is missing."""

    if not file_path.exists():
        raise FileNotFoundError(
            "Required RetailIQ artifact was not found: "
            f"{file_path}"
        )

    return file_path


@st.cache_data(show_spinner=False)
def load_customer_segments() -> pd.DataFrame:
    """Load customer-level cluster assignments."""

    file_path = require_file(
        PROCESSED_DATA_DIR
        / "customer_segments.csv.gz"
    )

    customer_segments = pd.read_csv(
        file_path,
        compression="gzip",
        low_memory=False,
    )

    customer_segments["CustomerID"] = (
        pd.to_numeric(
            customer_segments["CustomerID"],
            errors="coerce",
        )
        .astype("Int64")
    )

    customer_segments["Cluster"] = (
        pd.to_numeric(
            customer_segments["Cluster"],
            errors="raise",
        )
        .astype(int)
    )

    return customer_segments


@st.cache_data(show_spinner=False)
def load_customer_cluster_profile() -> pd.DataFrame:
    """Load the business profile for each cluster."""

    file_path = require_file(
        REPORT_TABLES_DIR
        / "customer_cluster_profile.csv"
    )

    cluster_profile = pd.read_csv(
        file_path
    )

    cluster_profile["Cluster"] = (
        pd.to_numeric(
            cluster_profile["Cluster"],
            errors="raise",
        )
        .astype(int)
    )

    return cluster_profile


@st.cache_data(show_spinner=False)
def load_customer_cluster_centres() -> pd.DataFrame:
    """Load cluster centres expressed in raw RFM units."""

    file_path = require_file(
        REPORT_TABLES_DIR
        / "customer_cluster_centres.csv"
    )

    cluster_centres = pd.read_csv(
        file_path
    )

    cluster_centres["Cluster"] = (
        pd.to_numeric(
            cluster_centres["Cluster"],
            errors="raise",
        )
        .astype(int)
    )

    return cluster_centres


@st.cache_data(show_spinner=False)
def load_customer_segmentation_metrics() -> pd.Series:
    """Load customer-segmentation model metrics."""

    file_path = require_file(
        REPORT_METRICS_DIR
        / "customer_segmentation_metrics.csv"
    )

    metrics_df = pd.read_csv(
        file_path
    )

    return (
        metrics_df
        .set_index("Metric")["Value"]
    )


@st.cache_data(show_spinner=False)
def load_customer_segmentation_metadata() -> dict:
    """Load segmentation configuration and metadata."""

    file_path = require_file(
        MODELS_DIR
        / "customer_segmentation_metadata.json"
    )

    return json.loads(
        file_path.read_text(
            encoding="utf-8"
        )
    )


@st.cache_resource(show_spinner=False)
def load_customer_segmentation_pipeline():
    """Load the fitted segmentation pipeline."""

    file_path = require_file(
        MODELS_DIR
        / "customer_segmentation_pipeline.joblib"
    )

    return joblib.load(file_path)

@st.cache_data(show_spinner=False)
def load_product_lifecycle() -> pd.DataFrame:
    """Load product lifecycle and ABC analysis."""

    file_path = require_file(
        EDA_DATA_DIR
        / "product_lifecycle.csv"
    )

    product_lifecycle = pd.read_csv(
        file_path,
        low_memory=False,
    )

    # Standardise the saved index/stock-code column.
    if (
        "StockCodeNormalized"
        not in product_lifecycle.columns
    ):
        if "StockCode" in product_lifecycle.columns:
            product_lifecycle = (
                product_lifecycle.rename(
                    columns={
                        "StockCode": (
                            "StockCodeNormalized"
                        )
                    }
                )
            )

        elif "Unnamed: 0" in product_lifecycle.columns:
            product_lifecycle = (
                product_lifecycle.rename(
                    columns={
                        "Unnamed: 0": (
                            "StockCodeNormalized"
                        )
                    }
                )
            )

    required_columns = {
        "StockCodeNormalized",
        "Description",
        "Revenue",
        "UnitsSold",
        "Orders",
        "FirstSale",
        "LastSale",
        "DaysSinceLastSale",
        "ABCClass",
    }

    missing_columns = required_columns.difference(
        product_lifecycle.columns
    )

    if missing_columns:
        raise KeyError(
            "Product lifecycle file is missing: "
            f"{sorted(missing_columns)}"
        )

    product_lifecycle[
        "StockCodeNormalized"
    ] = (
        product_lifecycle[
            "StockCodeNormalized"
        ]
        .astype("string")
        .str.strip()
        .str.upper()
    )

    for date_column in [
        "FirstSale",
        "LastSale",
    ]:
        product_lifecycle[date_column] = (
            pd.to_datetime(
                product_lifecycle[date_column],
                errors="coerce",
            )
        )

    for numeric_column in [
        "Revenue",
        "UnitsSold",
        "Orders",
        "DaysSinceLastSale",
    ]:
        product_lifecycle[numeric_column] = (
            pd.to_numeric(
                product_lifecycle[numeric_column],
                errors="coerce",
            )
        )

    product_lifecycle["ABCClass"] = (
        product_lifecycle["ABCClass"]
        .astype("string")
        .str.strip()
        .str.upper()
    )

    return product_lifecycle


@st.cache_data(show_spinner=False)
def load_market_basket_rules() -> pd.DataFrame:
    """Load human-readable actionable association rules."""

    file_path = require_file(
        MARKET_BASKET_DATA_DIR
        / "visualization_rules.csv"
    )

    basket_rules = pd.read_csv(
        file_path,
        low_memory=False,
    )

    required_columns = {
        "AntecedentProducts",
        "ConsequentProducts",
        "support",
        "confidence",
        "lift",
        "BasketCount",
    }

    missing_columns = required_columns.difference(
        basket_rules.columns
    )

    if missing_columns:
        raise KeyError(
            "Market-basket rules file is missing: "
            f"{sorted(missing_columns)}"
        )

    for numeric_column in [
        "support",
        "confidence",
        "lift",
        "BasketCount",
    ]:
        basket_rules[numeric_column] = (
            pd.to_numeric(
                basket_rules[numeric_column],
                errors="coerce",
            )
        )

    return basket_rules.dropna(
        subset=[
            "AntecedentProducts",
            "ConsequentProducts",
            "support",
            "confidence",
            "lift",
        ]
    )


@st.cache_data(show_spinner=False)
def load_market_basket_rules() -> pd.DataFrame:
    """Load and standardise actionable association rules."""

    file_path = require_file(
        MARKET_BASKET_DATA_DIR
        / "visualization_rules.csv"
    )

    basket_rules = pd.read_csv(
        file_path,
        low_memory=False,
    )

    # Remove accidental spaces from column names.
    basket_rules.columns = (
        basket_rules.columns
        .astype(str)
        .str.strip()
    )

    # Map variations to canonical dashboard names.
    column_aliases = {
        "antecedentproducts": "AntecedentProducts",
        "antecedent_products": "AntecedentProducts",
        "antecedents": "AntecedentProducts",

        "consequentproducts": "ConsequentProducts",
        "consequent_products": "ConsequentProducts",
        "consequents": "ConsequentProducts",

        "support": "support",
        "supportpercent": "support",
        "support_percent": "support",

        "confidence": "confidence",
        "confidencepercent": "confidence",
        "confidence_percent": "confidence",

        "lift": "lift",

        "basketcount": "BasketCount",
        "basket_count": "BasketCount",
        "supportcount": "BasketCount",
        "support_count": "BasketCount",
    }

    rename_columns = {}

    for original_column in basket_rules.columns:
        normalised_column = (
            original_column
            .replace(" ", "")
            .replace("-", "")
            .lower()
        )

        if normalised_column in column_aliases:
            rename_columns[original_column] = (
                column_aliases[
                    normalised_column
                ]
            )

    basket_rules = basket_rules.rename(
        columns=rename_columns
    )

    required_columns = {
        "AntecedentProducts",
        "ConsequentProducts",
        "support",
        "confidence",
        "lift",
        "BasketCount",
    }

    missing_columns = required_columns.difference(
        basket_rules.columns
    )

    if missing_columns:
        raise KeyError(
            "Market-basket rules file is missing "
            f"{sorted(missing_columns)}. "
            f"Available columns: "
            f"{basket_rules.columns.tolist()}"
        )

    for numeric_column in [
        "support",
        "confidence",
        "lift",
        "BasketCount",
    ]:
        basket_rules[numeric_column] = (
            pd.to_numeric(
                basket_rules[numeric_column],
                errors="coerce",
            )
        )

    # Convert percentage values to proportions when necessary.
    if basket_rules["support"].max() > 1:
        basket_rules["support"] = (
            basket_rules["support"] / 100
        )

    if basket_rules["confidence"].max() > 1:
        basket_rules["confidence"] = (
            basket_rules["confidence"] / 100
        )

    basket_rules = basket_rules.dropna(
        subset=[
            "AntecedentProducts",
            "ConsequentProducts",
            "support",
            "confidence",
            "lift",
            "BasketCount",
        ]
    )

    return (
        basket_rules
        .sort_values(
            [
                "lift",
                "confidence",
                "support",
            ],
            ascending=False,
        )
        .reset_index(drop=True)
    )

@st.cache_data(show_spinner=False)
def load_market_basket_summary() -> pd.DataFrame:
    """Load market-basket summary metrics."""

    file_path = require_file(
        MARKET_BASKET_DATA_DIR
        / "market_basket_summary.csv"
    )

    return pd.read_csv(
        file_path,
        low_memory=False,
    )

def _read_anomaly_table(
    filename: str,
) -> pd.DataFrame:
    """Read and lightly standardise an anomaly table."""

    file_path = require_file(
        ANOMALY_DATA_DIR / filename
    )

    dataframe = pd.read_csv(
        file_path,
        low_memory=False,
    )

    dataframe.columns = (
        dataframe.columns
        .astype(str)
        .str.strip()
    )

    if "Invoice" in dataframe.columns:
        dataframe["Invoice"] = (
            dataframe["Invoice"]
            .astype("string")
            .str.strip()
        )

    if "CustomerID" in dataframe.columns:
        dataframe["CustomerID"] = (
            pd.to_numeric(
                dataframe["CustomerID"],
                errors="coerce",
            )
            .astype("Int64")
        )

    possible_date_columns = [
        "InvoiceDate",
        "FirstInvoiceDate",
        "LastInvoiceDate",
        "InvoiceMonth",
        "Month",
    ]

    for date_column in possible_date_columns:
        if date_column in dataframe.columns:
            dataframe[date_column] = (
                pd.to_datetime(
                    dataframe[date_column],
                    errors="coerce",
                )
            )

    return dataframe


@st.cache_data(show_spinner=False)
def load_anomaly_invoice_cases() -> pd.DataFrame:
    """Load the final invoice-level review queue."""

    return _read_anomaly_table(
        "anomaly_invoice_cases.csv.gz"
    )


@st.cache_data(show_spinner=False)
def load_anomaly_flagged_lines() -> pd.DataFrame:
    """Load transaction lines linked to anomaly cases."""

    return _read_anomaly_table(
        "anomaly_flagged_lines.csv.gz"
    )


@st.cache_data(show_spinner=False)
def load_anomaly_case_summary() -> pd.DataFrame:
    """Load case summary by priority and category."""

    return _read_anomaly_table(
        "anomaly_case_summary.csv"
    )


@st.cache_data(show_spinner=False)
def load_anomaly_monthly_metrics() -> pd.DataFrame:
    """Load monthly anomaly-monitoring metrics."""

    return _read_anomaly_table(
        "anomaly_monthly_metrics.csv"
    )


@st.cache_data(show_spinner=False)
def load_anomaly_ensemble_stability() -> pd.DataFrame:
    """Load ensemble stability diagnostics."""

    return _read_anomaly_table(
        "anomaly_ensemble_stability.csv"
    )


@st.cache_data(show_spinner=False)
def load_anomaly_ensemble_summary() -> pd.DataFrame:
    """Load aggregate ensemble-stability results."""

    return _read_anomaly_table(
        "anomaly_ensemble_summary.csv"
    )


@st.cache_data(show_spinner=False)
def load_anomaly_line_validation() -> pd.DataFrame:
    """Load final line-level validation metrics."""

    return _read_anomaly_table(
        "anomaly_line_validation.csv"
    )


@st.cache_data(show_spinner=False)
def load_anomaly_case_validation() -> pd.DataFrame:
    """Load final invoice-case validation metrics."""

    return _read_anomaly_table(
        "anomaly_case_validation.csv"
    )


@st.cache_data(show_spinner=False)
def load_anomaly_metadata() -> dict:
    """Load anomaly-model metadata."""

    file_path = require_file(
        ANOMALY_MODELS_DIR
        / "model_metadata.json"
    )

    return json.loads(
        file_path.read_text(
            encoding="utf-8"
        )
    )


@st.cache_resource(show_spinner=False)
def load_anomaly_model():
    """Load the fitted Isolation Forest ensemble."""

    file_path = require_file(
        ANOMALY_MODELS_DIR
        / "isolation_forest_ensemble_v1.joblib"
    )

    return joblib.load(file_path)



@st.cache_data(show_spinner=False)
def load_forecast_model_comparison():
    forecast_comparison = pd.read_csv(
        require_file(
            FORECAST_COMPARISON_FILE
        )
    )

    required_columns = {
        "Model",
        "Observations",
        "MAE",
        "RMSE",
        "WAPEPercent",
        "SMAPEPercent",
        "BiasPercent",
        "WAPERank"
    }

    missing_columns = (
        required_columns
        - set(forecast_comparison.columns)
    )

    if missing_columns:
        raise KeyError(
            "Forecast comparison is missing: "
            f"{sorted(missing_columns)}"
        )

    return (
        forecast_comparison
        .sort_values("WAPERank")
        .reset_index(drop=True)
    )


@st.cache_data(show_spinner=False)
def load_forecast_test_predictions():
    test_predictions = pd.read_csv(
        require_file(
            FORECAST_TEST_PREDICTIONS_FILE
        ),
        parse_dates=["ForecastDate"]
    )

    required_columns = {
        "ForecastDate",
        "ActualRevenue",
        "BaselinePrediction",
        "XGBoostPrediction",
        "LSTMPrediction"
    }

    missing_columns = (
        required_columns
        - set(test_predictions.columns)
    )

    if missing_columns:
        raise KeyError(
            "Forecast test predictions are missing: "
            f"{sorted(missing_columns)}"
        )

    return (
        test_predictions
        .sort_values("ForecastDate")
        .reset_index(drop=True)
    )


@st.cache_data(show_spinner=False)
def load_future_revenue_forecast():
    future_forecast = pd.read_csv(
        require_file(
            FUTURE_REVENUE_FORECAST_FILE
        ),
        parse_dates=["ForecastDate"]
    )

    required_columns = {
        "ForecastDate",
        "ForecastHorizonDay",
        "PredictedRevenue",
        "Model",
        "LowerRevenueEstimate",
        "UpperRevenueEstimate"
    }

    missing_columns = (
        required_columns
        - set(future_forecast.columns)
    )

    if missing_columns:
        raise KeyError(
            "Future revenue forecast is missing: "
            f"{sorted(missing_columns)}"
        )

    return (
        future_forecast
        .sort_values("ForecastDate")
        .reset_index(drop=True)
    )


@st.cache_data(show_spinner=False)
def load_forecast_metadata():
    metadata_path = require_file(
        FORECAST_METADATA_FILE
    )

    with metadata_path.open(
        "r",
        encoding="utf-8"
    ) as metadata_file:
        return json.load(metadata_file)


def get_forecast_test_figure_path():
    return require_file(
        FORECAST_TEST_FIGURE_FILE
    )


def get_future_forecast_figure_path():
    return require_file(
        FUTURE_FORECAST_FIGURE_FILE
    )

def get_forecast_model_wape_figure_path():
    return require_file(
        FORECAST_MODEL_WAPE_FIGURE_FILE
    )