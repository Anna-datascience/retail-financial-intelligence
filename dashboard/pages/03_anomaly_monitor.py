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
# Anomaly score and flagged revenue
# ---------------------------------------------------------

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

st.subheader("Invoice review map: anomaly score and flagged revenue")

revenue_scale = st.radio(
    "Revenue scale",
    ["Log-like", "Linear"],
    horizontal=True,
    key="anomaly_revenue_scale",
    help=(
        "Log-like spreads out smaller amounts while keeping zeros visible. "
        "Linear shows the original differences in pounds."
    ),
)

# Use the existing filtered cases without changing the source dataframe.
score_plot_df = invoice_cases.copy()

for column in ["MaximumAnomalyScore", "AlertRevenue"]:
    score_plot_df[column] = pd.to_numeric(
        score_plot_df[column],
        errors="coerce",
    ).astype(float)

valid_coordinates = (
    np.isfinite(score_plot_df["MaximumAnomalyScore"])
    & np.isfinite(score_plot_df["AlertRevenue"])
)

invalid_count = int((~valid_coordinates).sum())

if invalid_count:
    st.warning(
        f"{invalid_count:,} cases cannot be plotted because their "
        "score or flagged revenue is missing or invalid."
    )

score_plot_df = score_plot_df.loc[valid_coordinates].copy()

if score_plot_df.empty:
    st.info("No cases available for the current filters.")

else:
    # Display identifiers as text, including missing customer IDs.
    for column in ["CaseID", "Invoice", "CustomerID"]:
        score_plot_df[column] = (
            score_plot_df[column]
            .astype("string")
            .fillna("Unknown")
        )

    revenue = score_plot_df["AlertRevenue"]

    if revenue_scale == "Log-like":
        # Signed log1p: preserves zeros and the sign of negative amounts.
        score_plot_df["_RevenueAxis"] = (
            np.sign(revenue) * np.log10(1 + np.abs(revenue))
        )
        revenue_axis_title = "Flagged line revenue (£, log-like scale)"
    else:
        score_plot_df["_RevenueAxis"] = revenue
        revenue_axis_title = "Flagged line revenue (£)"

    score_chart = px.scatter(
        score_plot_df,
        x="MaximumAnomalyScore",
        y="_RevenueAxis",
        color="CasePriority",
        color_discrete_map=PRIORITY_COLORS,
        category_orders={"CasePriority": PRIORITY_ORDER},
        hover_name="CaseID",
        hover_data={
            "_RevenueAxis": False,
            "MaximumAnomalyScore": ":.3f",
            "AlertRevenue": ":,.2f",
            "Invoice": True,
            "CustomerID": True,
            "AlertLines": True,
            "PrimaryAlertCategory": True,
            "BusinessOwner": True,
            "AlertLineSharePercent": ":.1f",
            "AverageModelVotes": ":.2f",
        },
        labels={
            "MaximumAnomalyScore": "Maximum ensemble anomaly score",
            "_RevenueAxis": revenue_axis_title,
            "AlertRevenue": "Flagged line revenue (£)",
            "CasePriority": "Priority",
            "CustomerID": "Customer",
            "AlertLines": "Flagged lines",
            "PrimaryAlertCategory": "Alert category",
            "BusinessOwner": "Review owner",
            "AlertLineSharePercent": "Flagged lines (%)",
            "AverageModelVotes": "Average model votes",
        },
        template="plotly_white",
        render_mode="svg",
    )

    # Equal-size dots make smaller cases easier to see.
    score_chart.update_traces(
        marker={
            "size": 9,
            "opacity": 0.70,
            "line": {"width": 0.5, "color": "white"},
        },
    )

    if revenue_scale == "Log-like":
        # Tick positions are transformed; labels remain actual GBP amounts.
        largest_amount = max(1.0, float(revenue.abs().max()))
        max_power = max(1, int(np.ceil(np.log10(largest_amount))))

        tick_amounts = np.r_[
            0.0,
            10.0 ** np.arange(1, max_power + 1),
        ]

        if revenue.lt(0).any():
            tick_amounts = np.unique(
                np.r_[-tick_amounts, tick_amounts]
            )

        score_chart.update_yaxes(
            tickmode="array",
            tickvals=(
                np.sign(tick_amounts)
                * np.log10(1 + np.abs(tick_amounts))
            ),
            ticktext=[
                f"-£{abs(amount):,.0f}"
                if amount < 0
                else f"£{amount:,.0f}"
                for amount in tick_amounts
            ],
        )
    else:
        score_chart.update_yaxes(
            tickprefix="£",
            tickformat=",.0f",
        )

    score_chart.update_layout(
        height=540,
        margin={"l": 75, "r": 30, "t": 85, "b": 65},
        hovermode="closest",
        hoverlabel={"font_size": 12},
        legend={
            "title_text": "",
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.04,
            "xanchor": "left",
            "x": 0,
        },
    )

    # Label only the two largest amounts within the current filters.
    largest_cases = score_plot_df.nlargest(2, "AlertRevenue")

    for position, (_, case) in enumerate(largest_cases.iterrows()):
        score_chart.add_annotation(
            x=case["MaximumAnomalyScore"],
            y=case["_RevenueAxis"],
            text=(
                f"Invoice {case['Invoice']}<br>"
                f"£{case['AlertRevenue']:,.0f}"
            ),
            showarrow=True,
            arrowhead=2,
            ax=-110,
            ay=-35 if position == 0 else 40,
            bgcolor="rgba(255,255,255,0.95)",
            bordercolor="#CBD5E1",
            borderpad=4,
            font={"size": 11, "color": "#334155"},
        )

    st.plotly_chart(
        score_chart,
        width="stretch",
        key="anomaly_score_revenue_chart",
        config={"displaylogo": False},
    )

    st.caption(
        "Each dot represents one invoice review case. Moving right means "
        "a higher anomaly score; moving up means higher flagged line revenue. "
        "Colour indicates review priority; dot size is constant. "
        "Scores are not fraud probabilities, and flagged revenue is not "
        "confirmed financial loss."
    )

    if revenue_scale == "Log-like":
        st.caption(
            "The log-like scale compresses large amounts and retains zeros. "
            "Axis labels and hover details show the original GBP amounts."
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