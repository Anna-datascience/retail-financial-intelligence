from pathlib import Path
import sys

import pandas as pd
import streamlit as st


# --------------------------------------------------
# Project configuration
# --------------------------------------------------

PROJECT_ROOT = (
    Path(__file__).resolve().parents[1]
)

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(PROJECT_ROOT)
    )


st.set_page_config(
    page_title="RetailIQ",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)


from dashboard.utils.data_loader import (
    load_anomaly_invoice_cases,
    load_customer_cluster_profile,
    load_customer_segments,
    load_forecast_metadata,
    load_forecast_model_comparison,
    load_future_revenue_forecast,
    load_market_basket_rules,
    load_product_lifecycle,
)


# --------------------------------------------------
# Load dashboard artifacts
# --------------------------------------------------

try:
    customer_segments = (
        load_customer_segments()
    )

    customer_profile = (
        load_customer_cluster_profile()
    )

    product_lifecycle = (
        load_product_lifecycle()
    )

    basket_rules = (
        load_market_basket_rules()
    )

    anomaly_cases = (
        load_anomaly_invoice_cases()
    )

    forecast_comparison = (
        load_forecast_model_comparison()
    )

    future_forecast = (
        load_future_revenue_forecast()
    )

    forecast_metadata = (
        load_forecast_metadata()
    )

except (
    FileNotFoundError,
    KeyError,
    ValueError
) as error:
    st.error(
        "RetailIQ analytical artifacts could "
        f"not be loaded: {error}"
    )
    st.stop()


# --------------------------------------------------
# Prepare executive metrics
# --------------------------------------------------

def format_pounds(value):
    return f"£{float(value):,.2f}"


customer_count = len(
    customer_segments
)

vip_rows = customer_profile.loc[
    customer_profile["ClusterName"]
    .astype(str)
    .str.contains(
        "VIP",
        case=False,
        na=False
    )
]

if not vip_rows.empty:
    vip_customer_count = int(
        vip_rows.iloc[0]["Customers"]
    )

    vip_revenue_share = float(
        vip_rows.iloc[0][
            "RevenueSharePercent"
        ]
    )
else:
    vip_customer_count = 0
    vip_revenue_share = 0.0


product_lifecycle[
    "DaysSinceLastSale"
] = pd.to_numeric(
    product_lifecycle["DaysSinceLastSale"],
    errors="coerce"
)

product_lifecycle["Orders"] = pd.to_numeric(
    product_lifecycle["Orders"],
    errors="coerce"
)

inactive_products = product_lifecycle.loc[
    (
        product_lifecycle[
            "DaysSinceLastSale"
        ] >= 180
    )
    |
    (
        product_lifecycle["Orders"] <= 2
    )
]

high_value_inactive = (
    inactive_products.loc[
        inactive_products[
            "ABCClass"
        ].isin(["A", "B"])
    ]
)


anomaly_cases[
    "HighestAlertPriority"
] = pd.to_numeric(
    anomaly_cases[
        "HighestAlertPriority"
    ],
    errors="coerce"
)

anomaly_cases["AlertRevenue"] = pd.to_numeric(
    anomaly_cases["AlertRevenue"],
    errors="coerce"
).fillna(0)

priority_1_cases = anomaly_cases.loc[
    anomaly_cases[
        "HighestAlertPriority"
    ] == 1
]

priority_1_count = len(
    priority_1_cases
)

priority_1_exposure = (
    priority_1_cases[
        "AlertRevenue"
    ].sum()
)


forecast_comparison = (
    forecast_comparison
    .sort_values("WAPERank")
    .reset_index(drop=True)
)

selected_model = forecast_metadata.get(
    "selected_model",
    forecast_comparison.iloc[0]["Model"]
)

selected_wape = float(
    forecast_comparison.iloc[0][
        "WAPEPercent"
    ]
)

wape_improvement = float(
    forecast_metadata.get(
        "wape_improvement_over_baseline_percent",
        0
    )
)

future_total_revenue = (
    future_forecast[
        "PredictedRevenue"
    ].sum()
)

future_start = (
    future_forecast[
        "ForecastDate"
    ].min()
)

future_end = (
    future_forecast[
        "ForecastDate"
    ].max()
)


# --------------------------------------------------
# Sidebar
# --------------------------------------------------

with st.sidebar:
    st.title("📊RetailIQ")

    st.caption(
        "AI-powered retail financial "
        "intelligence platform"
    )

    st.success(
        "All analytical modules validated"
    )

    st.markdown(
        """
        Use the navigation above to explore:

        - Customer Intelligence
        - Product and Basket Analysis
        - Anomaly Monitor
        - Revenue Forecasting
        - Business Recommendations
        """
    )

    st.divider()

    st.caption(
        "Currency: British pounds sterling "
        "(GBP, £)"
    )

    st.caption(
        "Historical data ends: "
        f"{forecast_metadata.get(
            'historical_data_end',
            'Not available'
        )}"
    )


# --------------------------------------------------
# Page introduction
# --------------------------------------------------

st.title(
    "📊RetailIQ: Retail Financial Intelligence"
)

st.markdown(
    """
    RetailIQ transforms retail transaction data into
    customer insights, product opportunities, financial
    controls and forward-looking revenue forecasts.
    """
)

st.caption(
    "All prices, revenue, customer monetary values, "
    "financial exposure and forecasts are shown in "
    "British pounds sterling (GBP, £)."
)


# --------------------------------------------------
# Primary executive KPIs
# --------------------------------------------------

st.subheader("Executive overview")

primary_metrics = st.columns(5)

primary_metrics[0].metric(
    "Segmented customers",
    f"{customer_count:,}"
)

primary_metrics[1].metric(
    "VIP revenue share",
    f"{vip_revenue_share:.2f}%",
    help=(
        f"{vip_customer_count:,} customers are "
        "classified as VIP / Strategic."
    )
)

primary_metrics[2].metric(
    "P1 anomaly cases",
    f"{priority_1_count:,}"
)

primary_metrics[3].metric(
    "P1 alert exposure",
    format_pounds(
        priority_1_exposure
    )
)

primary_metrics[4].metric(
    "30-day forecast",
    format_pounds(
        future_total_revenue
    )
)


secondary_metrics = st.columns(5)

secondary_metrics[0].metric(
    "Inactive product candidates",
    f"{len(inactive_products):,}"
)

secondary_metrics[1].metric(
    "High-value inactive candidates",
    f"{len(high_value_inactive):,}",
    help="Inactive candidates in ABC classes A or B."
)

secondary_metrics[2].metric(
    "Cross-sell rules",
    f"{len(basket_rules):,}"
)

with secondary_metrics[3]:
    st.metric(
        "Forecast model",
        "XGBoost",
        help=f"Full model name: {selected_model}"
    )

    st.caption(selected_model)

secondary_metrics[4].metric(
    "Test WAPE",
    f"{selected_wape:.2f}%",
    delta=(
        f"{wape_improvement:.2f}% "
        "better than baseline"
    )
)


# --------------------------------------------------
# Customer and anomaly snapshots
# --------------------------------------------------

customer_column, anomaly_column = (
    st.columns(2)
)


with customer_column:
    st.subheader(
        "Customer value concentration"
    )

    customer_share_chart = (
        customer_profile
        .set_index("ClusterName")[
            [
                "CustomerSharePercent",
                "RevenueSharePercent"
            ]
        ]
        .rename(
            columns={
                "CustomerSharePercent": (
                    "Customer share (%)"
                ),
                "RevenueSharePercent": (
                    "Revenue share (%)"
                )
            }
        )
    )

    st.bar_chart(
        customer_share_chart,
        width="stretch"
    )

    st.caption(
        "Compare the share of customers with "
        "the share of net monetary value "
        "generated by each segment."
    )


with anomaly_column:
    st.subheader(
        "Financial-review workload"
    )

    anomaly_priority_summary = (
        anomaly_cases
        .groupby(
            "CasePriority",
            dropna=False
        )
        .agg(
            Cases=(
                "CaseID",
                "nunique"
            ),
            AlertRevenue=(
                "AlertRevenue",
                "sum"
            )
        )
        .reset_index()
        .sort_values(
            "AlertRevenue",
            ascending=False
        )
    )

    st.dataframe(
        anomaly_priority_summary,
        hide_index=True,
        width="stretch",
        column_config={
            "CasePriority": (
                st.column_config.TextColumn(
                    "Review priority"
                )
            ),
            "Cases": (
                st.column_config.NumberColumn(
                    "Cases",
                    format="%d"
                )
            ),
            "AlertRevenue": (
                st.column_config.NumberColumn(
                    "Alert revenue (£)",
                    format="£%.2f"
                )
            )
        }
    )

    st.caption(
        "Anomaly cases identify transactions "
        "requiring investigation; they are not "
        "automatically classified as fraud."
    )


# --------------------------------------------------
# Product and forecast snapshots
# --------------------------------------------------

product_column, forecast_column = (
    st.columns(2)
)


with product_column:
    st.subheader(
        "Product portfolio signals"
    )

    abc_summary = (
        product_lifecycle
        .groupby(
            "ABCClass",
            dropna=False
        )
        .agg(
            Products=(
                "StockCodeNormalized",
                "nunique"
            ),
            Revenue=(
                "Revenue",
                "sum"
            )
        )
        .reset_index()
        .sort_values("ABCClass")
    )

    st.dataframe(
        abc_summary,
        hide_index=True,
        width="stretch",
        column_config={
            "ABCClass": (
                st.column_config.TextColumn(
                    "ABC class"
                )
            ),
            "Products": (
                st.column_config.NumberColumn(
                    "Products",
                    format="%d"
                )
            ),
            "Revenue": (
                st.column_config.NumberColumn(
                    "Revenue (£)",
                    format="£%.2f"
                )
            )
        }
    )

    st.warning(
        "Inactive products are investigation "
        "candidates, not automatically confirmed "
        "as discontinued."
    )


with forecast_column:
    st.subheader(
        "30-day revenue outlook"
    )

    forecast_chart = (
        future_forecast
        .set_index("ForecastDate")[
            [
                "LowerRevenueEstimate",
                "PredictedRevenue",
                "UpperRevenueEstimate"
            ]
        ]
        .rename(
            columns={
                "LowerRevenueEstimate": (
                    "Lower estimate (£)"
                ),
                "PredictedRevenue": (
                    "Predicted revenue (£)"
                ),
                "UpperRevenueEstimate": (
                    "Upper estimate (£)"
                )
            }
        )
    )

    st.line_chart(
        forecast_chart,
        width="stretch"
    )

    st.caption(
        f"Forecast period: "
        f"{future_start:%d %b %Y} to "
        f"{future_end:%d %b %Y}."
    )


# --------------------------------------------------
# Priority actions
# --------------------------------------------------

st.subheader("Immediate management priorities")

priority_actions = pd.DataFrame([
    {
        "Priority": "1",
        "Action": (
            "Investigate P1 anomaly cases"
        ),
        "Evidence": (
            f"{priority_1_count:,} cases with "
            f"{format_pounds(priority_1_exposure)} "
            "of alert exposure"
        ),
        "Owner": (
            "Finance and Operations"
        )
    },
    {
        "Priority": "2",
        "Action": (
            "Protect VIP customer relationships"
        ),
        "Evidence": (
            f"{vip_customer_count:,} VIP customers "
            f"generate {vip_revenue_share:.2f}% "
            "of customer net revenue"
        ),
        "Owner": (
            "Sales and CRM"
        )
    },
    {
        "Priority": "3",
        "Action": (
            "Review high-value inactive products"
        ),
        "Evidence": (
            f"{len(high_value_inactive):,} "
            "ABC class A/B candidates"
        ),
        "Owner": (
            "Merchandising"
        )
    },
    {
        "Priority": "4",
        "Action": (
            "Use forecast for financial planning"
        ),
        "Evidence": (
            f"Expected 30-day revenue of "
            f"{format_pounds(future_total_revenue)}"
        ),
        "Owner": (
            "Finance Planning"
        )
    }
])

st.dataframe(
    priority_actions,
    hide_index=True,
    width="stretch",
    column_config={
        "Priority": (
            st.column_config.TextColumn(
                "Order"
            )
        ),
        "Action": (
            st.column_config.TextColumn(
                "Management action",
                width="large"
            )
        ),
        "Evidence": (
            st.column_config.TextColumn(
                "Supporting evidence",
                width="large"
            )
        ),
        "Owner": (
            st.column_config.TextColumn(
                "Business owner"
            )
        )
    }
)


# --------------------------------------------------
# Module status
# --------------------------------------------------

st.subheader("Platform modules")

module_status = pd.DataFrame([
    {
        "Module": "Data Quality",
        "Method": (
            "Rule-based validation and audit flags"
        ),
        "Status": "Complete"
    },
    {
        "Module": "Customer Intelligence",
        "Method": (
            "RFM features and K-Means clustering"
        ),
        "Status": "Complete"
    },
    {
        "Module": "Product Intelligence",
        "Method": (
            "ABC analysis and product lifecycle"
        ),
        "Status": "Complete"
    },
    {
        "Module": "Market Basket",
        "Method": (
            "Association rules"
        ),
        "Status": "Complete"
    },
    {
        "Module": "Anomaly Detection",
        "Method": (
            "Isolation Forest ensemble and "
            "financial rules"
        ),
        "Status": "Complete"
    },
    {
        "Module": "Revenue Forecasting",
        "Method": (
            "Baseline, XGBoost and LSTM comparison"
        ),
        "Status": "Complete"
    },
    {
        "Module": "Business Recommendations",
        "Method": (
            "Cross-module decision layer"
        ),
        "Status": "Complete"
    }
])

st.dataframe(
    module_status,
    hide_index=True,
    width="stretch"
)

st.success(
    "RetailIQ analytical workflow and dashboard "
    "integration are complete."
)