from pathlib import Path
import sys

import pandas as pd
import streamlit as st


# --------------------------------------------------
# Project imports
# --------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dashboard.utils.data_loader import (  # noqa: E402
    load_anomaly_invoice_cases,
    load_customer_cluster_profile,
    load_forecast_metadata,
    load_forecast_model_comparison,
    load_future_revenue_forecast,
    load_market_basket_rules,
    load_product_lifecycle,
)


# --------------------------------------------------
# Load artifacts
# --------------------------------------------------

try:
    customer_profile = load_customer_cluster_profile()
    product_lifecycle = load_product_lifecycle()
    basket_rules = load_market_basket_rules()
    anomaly_cases = load_anomaly_invoice_cases()
    forecast_comparison = load_forecast_model_comparison()
    future_forecast = load_future_revenue_forecast()
    forecast_metadata = load_forecast_metadata()
except (FileNotFoundError, KeyError, ValueError) as error:
    st.error(f"Business-recommendation data could not be loaded: {error}")
    st.stop()


# --------------------------------------------------
# Helpers
# --------------------------------------------------

def format_pounds(value):
    return f"£{float(value):,.2f}"


def find_segment(segment_text):
    matches = customer_profile.loc[
        customer_profile["ClusterName"]
        .astype(str)
        .str.contains(segment_text, case=False, na=False)
    ]
    return None if matches.empty else matches.iloc[0]


def row_value(row, column, default=0):
    if row is None:
        return default
    value = row.get(column, default)
    return default if pd.isna(value) else value


# --------------------------------------------------
# Customer insights
# --------------------------------------------------

inactive_segment = find_segment("Inactive")
active_segment = find_segment("Active Core")
vip_segment = find_segment("VIP")

inactive_customers = int(row_value(inactive_segment, "Customers"))
active_customers = int(row_value(active_segment, "Customers"))
vip_customers = int(row_value(vip_segment, "Customers"))
active_revenue_share = float(row_value(active_segment, "RevenueSharePercent"))
vip_revenue_share = float(row_value(vip_segment, "RevenueSharePercent"))


# --------------------------------------------------
# Product and basket insights
# --------------------------------------------------

for numeric_column in ["DaysSinceLastSale", "Orders", "Revenue", "UnitsSold"]:
    if numeric_column in product_lifecycle.columns:
        product_lifecycle[numeric_column] = pd.to_numeric(
            product_lifecycle[numeric_column], errors="coerce"
        )

inactive_products = product_lifecycle.loc[
    product_lifecycle["DaysSinceLastSale"].ge(180)
    | product_lifecycle["Orders"].le(2)
].copy()

high_value_inactive_products = inactive_products.loc[
    inactive_products["ABCClass"].isin(["A", "B"])
].sort_values("Revenue", ascending=False)

for numeric_column in ["support", "confidence", "lift", "BasketCount"]:
    basket_rules[numeric_column] = pd.to_numeric(
        basket_rules[numeric_column], errors="coerce"
    )

ranked_basket_rules = basket_rules.sort_values(
    ["BasketCount", "confidence", "lift"],
    ascending=[False, False, False],
).copy()

if ranked_basket_rules.empty:
    top_rule_evidence = "No qualifying basket rule is available."
else:
    top_rule = ranked_basket_rules.iloc[0]
    top_rule_evidence = (
        f"{top_rule['AntecedentProducts']} → {top_rule['ConsequentProducts']}; "
        f"{float(top_rule['confidence']) * 100:.1f}% confidence and "
        f"{float(top_rule['lift']):.2f} lift."
    )


# --------------------------------------------------
# Anomaly insights
# --------------------------------------------------

anomaly_cases["HighestAlertPriority"] = pd.to_numeric(
    anomaly_cases["HighestAlertPriority"], errors="coerce"
)
anomaly_cases["AlertRevenue"] = pd.to_numeric(
    anomaly_cases["AlertRevenue"], errors="coerce"
).fillna(0)

priority_1_cases = anomaly_cases.loc[
    anomaly_cases["HighestAlertPriority"].eq(1)
]
priority_1_count = len(priority_1_cases)
priority_1_exposure = priority_1_cases["AlertRevenue"].sum()


# --------------------------------------------------
# Forecast insights
# --------------------------------------------------

forecast_comparison = (
    forecast_comparison.sort_values("WAPERank").reset_index(drop=True)
)
selected_forecast_model = forecast_metadata.get(
    "selected_model", forecast_comparison.iloc[0]["Model"]
)
selected_wape = float(forecast_comparison.iloc[0]["WAPEPercent"])
forecast_total = future_forecast["PredictedRevenue"].sum()
forecast_lower_total = future_forecast["LowerRevenueEstimate"].sum()
forecast_upper_total = future_forecast["UpperRevenueEstimate"].sum()
peak_forecast_row = future_forecast.loc[
    future_forecast["PredictedRevenue"].idxmax()
]
peak_forecast_date = peak_forecast_row["ForecastDate"].strftime("%d %b %Y")
peak_forecast_revenue = float(peak_forecast_row["PredictedRevenue"])


# --------------------------------------------------
# Management action plan
# --------------------------------------------------

action_plan = pd.DataFrame(
    [
        {
            "Priority": "P1",
            "BusinessArea": "Financial control",
            "Evidence": (
                f"{priority_1_count:,} immediate-review invoice cases represent "
                f"{format_pounds(priority_1_exposure)} of alert revenue."
            ),
            "RecommendedAction": (
                "Review invoice authorisation, quantities, prices and supporting "
                "documentation."
            ),
            "BusinessOwner": "Finance and Operations",
            "Timing": "Within 24–48 hours",
        },
        {
            "Priority": "P1",
            "BusinessArea": "Revenue planning",
            "Evidence": (
                f"{selected_forecast_model} achieved a test WAPE of "
                f"{selected_wape:.2f}%."
            ),
            "RecommendedAction": (
                "Use the 30-day forecast as the working cash-flow and capacity plan."
            ),
            "BusinessOwner": "Finance Planning",
            "Timing": "Review weekly",
        },
        {
            "Priority": "P2",
            "BusinessArea": "Strategic customers",
            "Evidence": (
                f"{vip_customers:,} VIP customers generate "
                f"{vip_revenue_share:.2f}% of customer net revenue."
            ),
            "RecommendedAction": (
                "Apply retention monitoring, service-level protection and "
                "account-specific offers."
            ),
            "BusinessOwner": "Sales and CRM",
            "Timing": "Review monthly",
        },
        {
            "Priority": "P2",
            "BusinessArea": "Core customers",
            "Evidence": (
                f"{active_customers:,} active-core customers generate "
                f"{active_revenue_share:.2f}% of customer net revenue."
            ),
            "RecommendedAction": (
                "Use cross-sell campaigns to increase purchase frequency and "
                "average order value."
            ),
            "BusinessOwner": "CRM and Marketing",
            "Timing": "Campaign cycle",
        },
        {
            "Priority": "P2",
            "BusinessArea": "Product portfolio",
            "Evidence": (
                f"{len(high_value_inactive_products):,} inactive candidates are "
                "classified as ABC class A or B."
            ),
            "RecommendedAction": (
                "Check availability, discontinuation status and replacement "
                "products before delisting."
            ),
            "BusinessOwner": "Merchandising",
            "Timing": "Within 30 days",
        },
        {
            "Priority": "P3",
            "BusinessArea": "Customer reactivation",
            "Evidence": (
                f"{inactive_customers:,} customers belong to the inactive or "
                "low-frequency segment."
            ),
            "RecommendedAction": (
                "Test a targeted reactivation campaign and measure incremental "
                "revenue against a control group."
            ),
            "BusinessOwner": "CRM and Marketing",
            "Timing": "Pilot campaign",
        },
        {
            "Priority": "P3",
            "BusinessArea": "Cross-selling",
            "Evidence": top_rule_evidence,
            "RecommendedAction": (
                "Pilot product bundles or contextual recommendations and measure "
                "incremental conversion."
            ),
            "BusinessOwner": "Marketing and Merchandising",
            "Timing": "Pilot and evaluate",
        },
    ]
)

priority_order = {"P1": 1, "P2": 2, "P3": 3}
action_plan["PriorityOrder"] = action_plan["Priority"].map(priority_order)
action_plan = (
    action_plan.sort_values(["PriorityOrder", "BusinessArea"])
    .drop(columns="PriorityOrder")
    .reset_index(drop=True)
)


# --------------------------------------------------
# Sidebar filters
# --------------------------------------------------

priority_options = ["P1", "P2", "P3"]
business_area_options = sorted(action_plan["BusinessArea"].dropna().unique())
business_owner_options = sorted(action_plan["BusinessOwner"].dropna().unique())
review_status_options = sorted(
    anomaly_cases["ReviewStatus"].dropna().astype(str).unique()
)
abc_class_options = sorted(
    inactive_products["ABCClass"].dropna().astype(str).unique()
)

with st.sidebar:
    st.header("Recommendation filters")

    priority_filter = st.multiselect(
        "Action priority", priority_options, default=priority_options
    )
    business_area_filter = st.multiselect(
        "Business area", business_area_options, default=business_area_options
    )
    business_owner_filter = st.multiselect(
        "Business owner", business_owner_options, default=business_owner_options
    )
    review_status_filter = st.multiselect(
        "Anomaly review status",
        review_status_options,
        default=review_status_options,
    )
    abc_class_filter = st.multiselect(
        "Inactive-product ABC class",
        abc_class_options,
        default=abc_class_options,
    )
    minimum_rule_confidence = st.slider(
        "Minimum cross-sell confidence",
        min_value=50,
        max_value=100,
        value=70,
        step=5,
        format="%d%%",
    )
    product_display_limit = st.slider(
        "Products to display", min_value=10, max_value=100, value=50, step=10
    )
    st.caption(
        "Executive KPIs show complete portfolio totals. Filters control the "
        "detailed recommendations and tables."
    )

filtered_action_plan = action_plan.loc[
    action_plan["Priority"].isin(priority_filter)
    & action_plan["BusinessArea"].isin(business_area_filter)
    & action_plan["BusinessOwner"].isin(business_owner_filter)
].copy()

filtered_anomaly_cases = anomaly_cases.loc[
    anomaly_cases["ReviewStatus"].astype(str).isin(review_status_filter)
].copy()

filtered_inactive_products = (
    inactive_products.loc[
        inactive_products["ABCClass"].astype(str).isin(abc_class_filter)
    ]
    .sort_values("Revenue", ascending=False)
    .copy()
)

filtered_basket_rules = ranked_basket_rules.loc[
    ranked_basket_rules["confidence"].ge(minimum_rule_confidence / 100)
].head(20)


# --------------------------------------------------
# Page header and executive KPIs
# --------------------------------------------------

st.title("💡 Business Recommendations")
st.caption(
    "Prioritized actions combining customer segmentation, product intelligence, "
    "anomaly monitoring and revenue forecasting. All monetary values are in "
    "British pounds sterling (GBP, £)."
)

kpi_columns = st.columns(5)
kpi_columns[0].metric("P1 anomaly cases", f"{priority_1_count:,}")
kpi_columns[1].metric(
    "P1 financial exposure", format_pounds(priority_1_exposure)
)
kpi_columns[2].metric("VIP revenue share", f"{vip_revenue_share:.2f}%")
kpi_columns[3].metric(
    "Inactive product candidates", f"{len(inactive_products):,}"
)
kpi_columns[4].metric("30-day revenue forecast", format_pounds(forecast_total))

st.set_page_config(
    page_title="Business Recommendations | RetailIQ",
    page_icon="💡",
    layout="wide",
)
# --------------------------------------------------
# Filtered management action plan
# --------------------------------------------------

st.subheader("Prioritized management action plan")

if filtered_action_plan.empty:
    st.warning("No management actions match the selected sidebar filters.")
else:
    st.dataframe(
        filtered_action_plan,
        hide_index=True,
        width="stretch",
        column_config={
            "BusinessArea": st.column_config.TextColumn("Business area"),
            "Evidence": st.column_config.TextColumn("Evidence", width="large"),
            "RecommendedAction": st.column_config.TextColumn(
                "Recommended action", width="large"
            ),
            "BusinessOwner": st.column_config.TextColumn("Business owner"),
        },
    )

st.download_button(
    label="Download displayed action plan",
    data=filtered_action_plan.to_csv(index=False).encode("utf-8"),
    file_name="retailiq_filtered_business_action_plan.csv",
    mime="text/csv",
)

customer_tab, product_tab, risk_tab, forecast_tab = st.tabs(
    ["Customer actions", "Product actions", "Financial controls", "Planning outlook"]
)


# --------------------------------------------------
# Customer actions
# --------------------------------------------------

with customer_tab:
    st.subheader("Customer-segment priorities")
    customer_share_chart = customer_profile.set_index("ClusterName")[
        ["CustomerSharePercent", "RevenueSharePercent"]
    ].rename(
        columns={
            "CustomerSharePercent": "Customer share (%)",
            "RevenueSharePercent": "Revenue share (%)",
        }
    )
    st.bar_chart(customer_share_chart, width="stretch")

    st.dataframe(
        customer_profile,
        hide_index=True,
        width="stretch",
        column_config={
            "TotalNetMonetary": st.column_config.NumberColumn(
                "Total net monetary value (£)", format="£%.2f"
            ),
            "AverageNetMonetary": st.column_config.NumberColumn(
                "Average net monetary value (£)", format="£%.2f"
            ),
            "AverageOrderValue": st.column_config.NumberColumn(
                "Average order value (£)", format="£%.2f"
            ),
            "CustomerSharePercent": st.column_config.NumberColumn(
                "Customer share (%)", format="%.2f%%"
            ),
            "RevenueSharePercent": st.column_config.NumberColumn(
                "Revenue share (%)", format="%.2f%%"
            ),
        },
    )


# --------------------------------------------------
# Product actions
# --------------------------------------------------

with product_tab:
    st.subheader("Filtered inactive-product review")
    st.warning(
        "Inactive products are review candidates, not automatically confirmed "
        "as discontinued."
    )

    product_columns = [
        "StockCodeNormalized",
        "Description",
        "Revenue",
        "UnitsSold",
        "Orders",
        "LastSale",
        "DaysSinceLastSale",
        "ABCClass",
    ]
    available_product_columns = [
        column for column in product_columns if column in filtered_inactive_products
    ]

    st.dataframe(
        filtered_inactive_products[available_product_columns].head(
            product_display_limit
        ),
        hide_index=True,
        width="stretch",
        column_config={
            "Revenue": st.column_config.NumberColumn(
                "Revenue (£)", format="£%.2f"
            ),
            "DaysSinceLastSale": st.column_config.NumberColumn(
                "Days since last sale", format="%d"
            ),
        },
    )

    st.subheader("Filtered cross-sell pilot candidates")
    if filtered_basket_rules.empty:
        st.warning("No basket rules meet the selected confidence threshold.")
    else:
        st.dataframe(
            filtered_basket_rules,
            hide_index=True,
            width="stretch",
            column_config={
                "support": st.column_config.NumberColumn(
                    "Support", format="%.3f"
                ),
                "confidence": st.column_config.NumberColumn(
                    "Confidence", format="%.3f"
                ),
                "lift": st.column_config.NumberColumn("Lift", format="%.2f"),
            },
        )


# --------------------------------------------------
# Financial controls
# --------------------------------------------------

with risk_tab:
    st.subheader("Filtered financial-control workload")

    filtered_priority_counts = filtered_anomaly_cases[
        "HighestAlertPriority"
    ].value_counts()
    risk_metrics = st.columns(4)
    risk_metrics[0].metric("Filtered cases", f"{len(filtered_anomaly_cases):,}")
    risk_metrics[1].metric("P1 cases", f"{filtered_priority_counts.get(1, 0):,}")
    risk_metrics[2].metric("P2 cases", f"{filtered_priority_counts.get(2, 0):,}")
    risk_metrics[3].metric("P3 cases", f"{filtered_priority_counts.get(3, 0):,}")

    risk_summary = (
        filtered_anomaly_cases.groupby("CasePriority", dropna=False)
        .agg(
            Cases=("CaseID", "nunique"),
            AlertRevenue=("AlertRevenue", "sum"),
            Customers=("CustomerID", "nunique"),
        )
        .reset_index()
        .sort_values("AlertRevenue", ascending=False)
    )

    st.dataframe(
        risk_summary,
        hide_index=True,
        width="stretch",
        column_config={
            "AlertRevenue": st.column_config.NumberColumn(
                "Alert revenue (£)", format="£%.2f"
            )
        },
    )

    review_columns = [
        "CaseID",
        "Invoice",
        "InvoiceDate",
        "CasePriority",
        "PrimaryAlertCategory",
        "AlertRevenue",
        "BusinessOwner",
        "ReviewStatus",
    ]
    available_review_columns = [
        column for column in review_columns if column in filtered_anomaly_cases
    ]

    st.dataframe(
        filtered_anomaly_cases.sort_values(
            ["HighestAlertPriority", "AlertRevenue"],
            ascending=[True, False],
        )[available_review_columns].head(50),
        hide_index=True,
        width="stretch",
        column_config={
            "AlertRevenue": st.column_config.NumberColumn(
                "Alert revenue (£)", format="£%.2f"
            )
        },
    )


# --------------------------------------------------
# Planning outlook
# --------------------------------------------------

with forecast_tab:
    st.subheader("30-day planning range")
    planning_metrics = st.columns(4)
    planning_metrics[0].metric("Central forecast", format_pounds(forecast_total))
    planning_metrics[1].metric(
        "Lower estimate", format_pounds(forecast_lower_total)
    )
    planning_metrics[2].metric(
        "Upper estimate", format_pounds(forecast_upper_total)
    )
    planning_metrics[3].metric(
        f"Peak day · {peak_forecast_date}", format_pounds(peak_forecast_revenue)
    )

    st.info(
        "Use the central forecast for the working plan and the lower/upper "
        "estimates for cash-flow and capacity sensitivity analysis."
    )

    st.dataframe(
        forecast_comparison,
        hide_index=True,
        width="stretch",
        column_config={
            "MAE": st.column_config.NumberColumn("MAE (£)", format="£%.2f"),
            "RMSE": st.column_config.NumberColumn("RMSE (£)", format="£%.2f"),
            "WAPEPercent": st.column_config.NumberColumn(
                "WAPE (%)", format="%.2f%%"
            ),
            "SMAPEPercent": st.column_config.NumberColumn(
                "SMAPE (%)", format="%.2f%%"
            ),
            "BiasPercent": st.column_config.NumberColumn(
                "Bias (%)", format="%.2f%%"
            ),
        },
    )
