"""RetailIQ anomaly monitoring dashboard."""

from pathlib import Path
import sys

import pandas as pd
import plotly.express as px
import streamlit as st


PROJECT_ROOT = (
    Path(__file__)
    .resolve()
    .parents[2]
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
)


st.set_page_config(
    page_title="Anomaly Monitor | RetailIQ",
    page_icon="🚨",
    layout="wide",
)


PRIORITY_ORDER = [
    "P1 - Immediate review",
    "P2 - Financial review",
    "P3 - Monitor",
]

PRIORITY_COLORS = {
    "P1 - Immediate review": "#C0392B",
    "P2 - Financial review": "#F39C12",
    "P3 - Monitor": "#3498DB",
}


@st.cache_data(show_spinner=False)
def prepare_download(
    dataframe: pd.DataFrame,
) -> bytes:
    return dataframe.to_csv(
        index=False
    ).encode("utf-8")


st.title("🚨 Financial Anomaly Monitor")

st.caption(
    "Invoice-level review queue produced by the "
    "Isolation Forest ensemble and financial control rules."
)

st.caption("All monetary values are shown in British pounds sterling (GBP).")

try:
    invoice_cases = (
        load_anomaly_invoice_cases()
    )

    case_summary = (
        load_anomaly_case_summary()
    )

    monthly_metrics = (
        load_anomaly_monthly_metrics()
    )

except (FileNotFoundError, KeyError) as error:
    st.error(str(error))
    st.stop()


invoice_cases = invoice_cases.copy()

invoice_cases["InvoiceDate"] = pd.to_datetime(
    invoice_cases["InvoiceDate"],
    errors="coerce",
)


# ---------------------------------------------------------
# Sidebar filters
# ---------------------------------------------------------

st.sidebar.header("Anomaly filters")

selected_priorities = st.sidebar.multiselect(
    "Case priority",
    options=PRIORITY_ORDER,
    default=PRIORITY_ORDER,
)

available_categories = sorted(
    invoice_cases[
        "PrimaryAlertCategory"
    ]
    .dropna()
    .unique()
    .tolist()
)

selected_categories = st.sidebar.multiselect(
    "Alert category",
    options=available_categories,
    default=available_categories,
)

available_owners = sorted(
    invoice_cases[
        "BusinessOwner"
    ]
    .dropna()
    .unique()
    .tolist()
)

selected_owners = st.sidebar.multiselect(
    "Business owner",
    options=available_owners,
    default=available_owners,
)

available_statuses = sorted(
    invoice_cases[
        "ReviewStatus"
    ]
    .dropna()
    .unique()
    .tolist()
)

selected_statuses = st.sidebar.multiselect(
    "Review status",
    options=available_statuses,
    default=available_statuses,
)

case_search = st.sidebar.text_input(
    "Search case or invoice",
    placeholder="ANOM-574941 or 574941",
)


filtered_cases = invoice_cases.loc[
    invoice_cases[
        "CasePriority"
    ].isin(selected_priorities)
    & invoice_cases[
        "PrimaryAlertCategory"
    ].isin(selected_categories)
    & invoice_cases[
        "BusinessOwner"
    ].isin(selected_owners)
    & invoice_cases[
        "ReviewStatus"
    ].isin(selected_statuses)
].copy()

if case_search.strip():
    search_value = case_search.strip()

    search_mask = (
        filtered_cases["CaseID"]
        .astype("string")
        .str.contains(
            search_value,
            case=False,
            regex=False,
            na=False,
        )
        |
        filtered_cases["Invoice"]
        .astype("string")
        .str.contains(
            search_value,
            case=False,
            regex=False,
            na=False,
        )
    )

    filtered_cases = filtered_cases.loc[
        search_mask
    ]


# ---------------------------------------------------------
# Executive KPIs
# ---------------------------------------------------------

total_cases = len(invoice_cases)

p1_cases = int(
    invoice_cases[
        "CasePriority"
    ]
    .eq("P1 - Immediate review")
    .sum()
)

model_flagged_invoices = int(
    invoice_cases[
        "ModelAlertLines"
    ].gt(0).sum()
)

baseline_only_invoices = int(
    (
        invoice_cases[
            "ModelAlertLines"
        ].eq(0)
        &
        invoice_cases[
            "BaselineAlertLines"
        ].gt(0)
    ).sum()
)

st.subheader("Alert overview")

kpi_1, kpi_2, kpi_3, kpi_4 = st.columns(4)

kpi_1.metric(
    "Invoice cases",
    f"{total_cases:,}",
)

kpi_2.metric(
    "P1 immediate review",
    f"{p1_cases:,}",
)

kpi_3.metric(
    "Model-flagged invoices",
    f"{model_flagged_invoices:,}",
)

kpi_4.metric(
    "Rule-only invoices",
    f"{baseline_only_invoices:,}",
)

# ---------------------------------------------------------
# Priority and category analysis
# ---------------------------------------------------------

st.subheader("Case priority and alert category")

chart_1, chart_2 = st.columns(2)

priority_summary = (
    invoice_cases[
        "CasePriority"
    ]
    .value_counts()
    .reindex(
        PRIORITY_ORDER,
        fill_value=0,
    )
    .rename_axis("CasePriority")
    .reset_index(name="Cases")
)

priority_chart = px.bar(
    priority_summary,
    x="CasePriority",
    y="Cases",
    color="CasePriority",
    color_discrete_map=PRIORITY_COLORS,
    text_auto=True,
    category_orders={
        "CasePriority": PRIORITY_ORDER
    },
    labels={
        "CasePriority": "",
        "Cases": "Invoice cases",
    },
)

priority_chart.update_layout(
    showlegend=False
)

chart_1.plotly_chart(
    priority_chart,
    width="stretch",
)


category_chart = px.bar(
    case_summary.sort_values(
        "Cases",
        ascending=True,
    ),
    x="Cases",
    y="PrimaryAlertCategory",
    orientation="h",
    color="CasePriority",
    color_discrete_map=PRIORITY_COLORS,
    category_orders={
        "CasePriority": PRIORITY_ORDER
    },
    hover_data={
        "BusinessOwner": True,
        "CaseRevenue": ":,.2f",
        "AverageCaseRevenue": ":,.2f",
    },
    labels={
        "PrimaryAlertCategory": "",
        "CasePriority": "Priority",
    },
)

category_chart.update_layout(
    legend_title_text=""
)

chart_2.plotly_chart(
    category_chart,
    width="stretch",
)


# ---------------------------------------------------------
# Monthly monitoring
# ---------------------------------------------------------

st.subheader("Monthly test-period stability")

monthly_metrics["InvoiceMonth"] = (
    pd.to_datetime(
        monthly_metrics["InvoiceMonth"],
        errors="coerce",
    )
)

monthly_rate_columns = [
    "AnomalyRatePercent",
    "FlaggedInvoiceRatePercent",
    "AlertRevenueSharePercent",
]

monthly_rates = (
    monthly_metrics[
        ["InvoiceMonth"] + monthly_rate_columns
    ]
    .melt(
        id_vars="InvoiceMonth",
        var_name="Metric",
        value_name="Percent",
    )
)

monthly_rates["Metric"] = (
    monthly_rates["Metric"]
    .replace(
        {
            "AnomalyRatePercent": (
                "Line anomaly rate"
            ),
            "FlaggedInvoiceRatePercent": (
                "Flagged invoice rate"
            ),
            "AlertRevenueSharePercent": (
                "Alert revenue share"
            ),
        }
    )
)

monthly_chart = px.line(
    monthly_rates,
    x="InvoiceMonth",
    y="Percent",
    color="Metric",
    markers=True,
    labels={
        "InvoiceMonth": "Month",
        "Percent": "Percent",
        "Metric": "",
    },
)

monthly_chart.update_yaxes(
    ticksuffix="%"
)

monthly_chart.update_xaxes(
    dtick="M1",
    tickformat="%b %Y",
)

st.plotly_chart(
    monthly_chart,
    width="stretch",
)


# ---------------------------------------------------------
# Business-owner workload
# ---------------------------------------------------------

st.subheader("Review workload by business owner")

owner_summary = (
    invoice_cases
    .groupby("BusinessOwner")
    .agg(
        Cases=("CaseID", "nunique"),
        P1Cases=(
            "HighestAlertPriority",
            lambda values: values.eq(1).sum(),
        ),
        AlertRevenue=("AlertRevenue", "sum"),
    )
    .reset_index()
    .sort_values(
        "Cases",
        ascending=True,
    )
)

owner_chart = px.bar(
    owner_summary,
    x="Cases",
    y="BusinessOwner",
    orientation="h",
    color="P1Cases",
    color_continuous_scale="Reds",
    text_auto=True,
    hover_data={
        "AlertRevenue": ":,.2f",
    },
    labels={
        "BusinessOwner": "",
        "Cases": "Cases",
        "P1Cases": "P1 cases",
    },
)

st.plotly_chart(
    owner_chart,
    width="stretch",
)


# ---------------------------------------------------------
# Score and financial exposure
# ---------------------------------------------------------

st.subheader("Anomaly score and financial exposure")

score_chart = px.scatter(
    invoice_cases,
    x="MaximumAnomalyScore",
    y="AlertRevenue",
    size="AlertLines",
    color="CasePriority",
    color_discrete_map=PRIORITY_COLORS,
    category_orders={
        "CasePriority": PRIORITY_ORDER
    },
    opacity=0.65,
    hover_data={
        "CaseID": True,
        "Invoice": True,
        "CustomerID": True,
        "PrimaryAlertCategory": True,
        "BusinessOwner": True,
        "AlertLineSharePercent": ":.1f",
        "AverageModelVotes": ":.2f",
    },
    labels={
        "MaximumAnomalyScore": (
            "Maximum ensemble anomaly score"
        ),
        "AlertRevenue": "Alert revenue",
        "CasePriority": "Priority",
        "AlertLines": "Alert lines",
    },
)

score_chart.update_layout(
    legend_title_text=""
)

st.plotly_chart(
    score_chart,
    width="stretch",
)


# ---------------------------------------------------------
# Priority guidance
# ---------------------------------------------------------

st.subheader("Review guidance")

guidance_1, guidance_2, guidance_3 = st.columns(3)

with guidance_1:
    st.markdown(
        """
        **P1 — Immediate review**

        Model and financial rules both identified unusual activity.
        Verify invoice authorisation, quantities, prices and customer
        context immediately.
        """
    )

with guidance_2:
    st.markdown(
        """
        **P2 — Financial review**

        Material financial extremes or contextual model anomalies.
        Review during the regular finance-control workflow.
        """
    )

with guidance_3:
    st.markdown(
        """
        **P3 — Monitor**

        Product novelty, new customers or limited customer context.
        Monitor patterns before escalation.
        """
    )


# ---------------------------------------------------------
# Case explorer
# ---------------------------------------------------------

st.subheader("Invoice review queue")

st.write(
    f"Showing **{len(filtered_cases):,}** cases."
)

case_columns = [
    "CaseID",
    "Invoice",
    "InvoiceDate",
    "CustomerID",
    "Country",
    "CasePriority",
    "PrimaryAlertCategory",
    "BusinessOwner",
    "AnalysedInvoiceRevenue",
    "AlertRevenue",
    "AlertLines",
    "AlertLineSharePercent",
    "MaximumAnomalyScore",
    "AverageModelVotes",
    "ReviewStatus",
]

case_table = (
    filtered_cases
    .sort_values(
        [
            "HighestAlertPriority",
            "AlertRevenue",
        ],
        ascending=[
            True,
            False,
        ],
    )
    .loc[
        :,
        case_columns
    ]
    .copy()
)

st.dataframe(
    case_table,
    width="stretch",
    hide_index=True,
    column_config={
        "CustomerID": (
            st.column_config.NumberColumn(
                "Customer ID",
                format="%d",
            )
        ),
        "AnalysedInvoiceRevenue": (
            st.column_config.NumberColumn(
                "Invoice revenue",
                format="%.2f",
            )
        ),
        "AlertRevenue": (
            st.column_config.NumberColumn(
                "Alert revenue",
                format="%.2f",
            )
        ),
        "AlertLineSharePercent": (
            st.column_config.NumberColumn(
                "Alert line share",
                format="%.1f%%",
            )
        ),
        "MaximumAnomalyScore": (
            st.column_config.NumberColumn(
                "Maximum score",
                format="%.3f",
            )
        ),
        "AverageModelVotes": (
            st.column_config.NumberColumn(
                "Average votes",
                format="%.2f",
            )
        ),
    },
)


# ---------------------------------------------------------
# Selected case details
# ---------------------------------------------------------

if not filtered_cases.empty:
    selected_case_id = st.selectbox(
        "Inspect an invoice case",
        options=filtered_cases[
            "CaseID"
        ].tolist(),
    )

    selected_case = (
        filtered_cases.loc[
            filtered_cases[
                "CaseID"
            ].eq(selected_case_id)
        ]
        .iloc[0]
    )

    detail_1, detail_2, detail_3 = st.columns(3)

    detail_1.metric(
        "Alert lines",
        f"{int(selected_case['AlertLines']):,}",
    )

    detail_2.metric(
        "Alert revenue",
        f"{selected_case['AlertRevenue']:,.2f}",
    )

    detail_3.metric(
        "Maximum score",
        f"{selected_case['MaximumAnomalyScore']:.3f}",
    )

    st.markdown(
        f"**Reason:** {selected_case['CaseReason']}"
    )

    st.markdown(
        "**Recommended action:** "
        f"{selected_case['RecommendedAction']}"
    )

    with st.expander(
        "All alert evidence"
    ):
        st.write(
            selected_case[
                "AllAlertCategories"
            ]
        )

        st.write(
            "**Financial-control reasons:**"
        )

        st.write(
            selected_case[
                "BaselineReasons"
            ]
        )


st.download_button(
    "Download filtered review queue",
    data=prepare_download(
        filtered_cases
    ),
    file_name=(
        "retailiq_anomaly_review_queue.csv"
    ),
    mime="text/csv",
)