from pathlib import Path
import sys

import pandas as pd


PROJECT_ROOT = (
    Path(__file__).resolve().parents[1]
)

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(PROJECT_ROOT)
    )


from dashboard.utils.data_loader import (
    load_anomaly_case_summary,
    load_anomaly_invoice_cases,
    load_anomaly_monthly_metrics,
    load_customer_cluster_profile,
    load_customer_segments,
    load_forecast_metadata,
    load_forecast_model_comparison,
    load_forecast_test_predictions,
    load_future_revenue_forecast,
    load_market_basket_rules,
    load_market_basket_summary,
    load_product_lifecycle,
)


failures = []


def check(
    check_name,
    condition,
    detail=""
):
    passed = bool(condition)
    status = "PASS" if passed else "FAIL"

    print(
        f"[{status}] {check_name}"
        + (
            f" — {detail}"
            if detail
            else ""
        )
    )

    if not passed:
        failures.append(check_name)


def check_columns(
    table,
    required_columns,
    table_name
):
    missing_columns = (
        set(required_columns)
        - set(table.columns)
    )

    check(
        f"{table_name} columns",
        not missing_columns,
        (
            f"missing={sorted(missing_columns)}"
            if missing_columns
            else "all required columns found"
        )
    )


# --------------------------------------------------
# Load all dashboard artifacts
# --------------------------------------------------

customer_segments = load_customer_segments()

customer_profile = (
    load_customer_cluster_profile()
)

product_lifecycle = load_product_lifecycle()

basket_rules = load_market_basket_rules()

basket_summary = load_market_basket_summary()

anomaly_cases = load_anomaly_invoice_cases()

anomaly_summary = load_anomaly_case_summary()

anomaly_monthly = (
    load_anomaly_monthly_metrics()
)

forecast_comparison = (
    load_forecast_model_comparison()
)

forecast_test = (
    load_forecast_test_predictions()
)

future_forecast = (
    load_future_revenue_forecast()
)

forecast_metadata = load_forecast_metadata()


# --------------------------------------------------
# Customer validation
# --------------------------------------------------

check(
    "Customer-segment rows",
    len(customer_segments) == 5839,
    f"rows={len(customer_segments)}"
)

check(
    "Customer clusters",
    len(customer_profile) == 3,
    f"clusters={len(customer_profile)}"
)

check_columns(
    customer_profile,
    [
        "ClusterName",
        "Customers",
        "AverageRecency",
        "AverageFrequency",
        "TotalNetMonetary",
        "CustomerSharePercent",
        "RevenueSharePercent"
    ],
    "Customer cluster profile"
)

check(
    "Customer shares total",
    abs(
        customer_profile[
            "CustomerSharePercent"
        ].sum()
        - 100
    ) < 0.1
)


# --------------------------------------------------
# Product and basket validation
# --------------------------------------------------

check(
    "Product lifecycle is populated",
    len(product_lifecycle) > 0,
    f"products={len(product_lifecycle)}"
)

check_columns(
    product_lifecycle,
    [
        "StockCodeNormalized",
        "Description",
        "Revenue",
        "UnitsSold",
        "Orders",
        "DaysSinceLastSale",
        "ABCClass"
    ],
    "Product lifecycle"
)

check(
    "Market-basket rules are populated",
    len(basket_rules) > 0,
    f"rules={len(basket_rules)}"
)

check_columns(
    basket_rules,
    [
        "AntecedentProducts",
        "ConsequentProducts",
        "support",
        "confidence",
        "lift",
        "BasketCount"
    ],
    "Market-basket rules"
)

check(
    "Market-basket summary is populated",
    len(basket_summary) > 0
)


# --------------------------------------------------
# Anomaly validation
# --------------------------------------------------

check(
    "Final anomaly cases",
    len(anomaly_cases) == 1009,
    f"cases={len(anomaly_cases)}"
)

anomaly_priority_counts = (
    anomaly_cases[
        "HighestAlertPriority"
    ]
    .value_counts()
    .to_dict()
)

check(
    "P1 anomaly cases",
    anomaly_priority_counts.get(1, 0) == 267,
    f"count={anomaly_priority_counts.get(1, 0)}"
)

check(
    "P2 anomaly cases",
    anomaly_priority_counts.get(2, 0) == 517,
    f"count={anomaly_priority_counts.get(2, 0)}"
)

check(
    "P3 anomaly cases",
    anomaly_priority_counts.get(3, 0) == 225,
    f"count={anomaly_priority_counts.get(3, 0)}"
)

check_columns(
    anomaly_cases,
    [
        "CaseID",
        "Invoice",
        "InvoiceDate",
        "HighestAlertPriority",
        "CasePriority",
        "PrimaryAlertCategory",
        "AlertRevenue",
        "BusinessOwner",
        "RecommendedAction",
        "ReviewStatus"
    ],
    "Anomaly invoice cases"
)

check(
    "Anomaly case summary is populated",
    len(anomaly_summary) > 0
)

check(
    "Anomaly monthly metrics populated",
    len(anomaly_monthly) > 0
)


# --------------------------------------------------
# Forecast validation
# --------------------------------------------------

check(
    "Forecast models",
    len(forecast_comparison) == 3,
    f"models={len(forecast_comparison)}"
)

check(
    "Forecast test observations",
    len(forecast_test) == 91,
    f"days={len(forecast_test)}"
)

check(
    "Future forecast observations",
    len(future_forecast) == 30,
    f"days={len(future_forecast)}"
)

check(
    "Forecast test start",
    forecast_test["ForecastDate"].min()
    == pd.Timestamp("2011-09-01")
)

check(
    "Forecast test end",
    forecast_test["ForecastDate"].max()
    == pd.Timestamp("2011-11-30")
)

selected_model = (
    forecast_metadata["selected_model"]
)

comparison_winner = (
    forecast_comparison
    .sort_values("WAPERank")
    .iloc[0]["Model"]
)

check(
    "Forecast selected model",
    selected_model
    == "Tuned XGBoost Raw Target",
    f"model={selected_model}"
)

check(
    "Forecast winner consistency",
    selected_model == comparison_winner,
    f"winner={comparison_winner}"
)

check(
    "Forecast currency",
    forecast_metadata.get("currency")
    == "GBP"
)

interval_is_valid = (
    (
        future_forecast[
            "LowerRevenueEstimate"
        ]
        <= future_forecast[
            "PredictedRevenue"
        ]
    )
    &
    (
        future_forecast[
            "PredictedRevenue"
        ]
        <= future_forecast[
            "UpperRevenueEstimate"
        ]
    )
).all()

check(
    "Forecast interval ordering",
    interval_is_valid
)


# --------------------------------------------------
# Forecast figure validation
# --------------------------------------------------

forecast_figure_directory = (
    PROJECT_ROOT
    / "reports"
    / "figures"
    / "revenue_forecasting"
)

required_forecast_figures = [
    "forecast_test_comparison.png",
    "forecast_model_wape_comparison.png",
    "future_30_day_revenue_forecast.png"
]

for figure_name in required_forecast_figures:
    figure_path = (
        forecast_figure_directory
        / figure_name
    )

    check(
        f"Forecast figure: {figure_name}",
        figure_path.exists()
    )


# --------------------------------------------------
# Final result
# --------------------------------------------------

print()

if failures:
    print(
        f"Dashboard validation failed with "
        f"{len(failures)} issue(s):"
    )

    for failure in failures:
        print(f" - {failure}")

    raise SystemExit(1)

print(
    "All RetailIQ dashboard artifact "
    "validations passed."
)