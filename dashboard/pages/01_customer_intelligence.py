"""RetailIQ customer intelligence dashboard page."""

from pathlib import Path
import sys

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st


# Ensure the project root is importable.
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
    load_customer_cluster_centres,
    load_customer_cluster_profile,
    load_customer_segmentation_metadata,
    load_customer_segmentation_metrics,
    load_customer_segments,
)


st.set_page_config(
    page_title="Customer Intelligence | RetailIQ",
    page_icon="🎯",
    layout="wide",
)


CLUSTER_COLORS = {
    "Inactive / Low Frequency": "#7F8C8D",
    "Active Core": "#2E86DE",
    "VIP / Strategic": "#F39C12",
}


@st.cache_data(show_spinner=False)
def prepare_customer_download(
    dataframe: pd.DataFrame,
) -> bytes:
    """Prepare customer data for download."""

    return dataframe.to_csv(
        index=False
    ).encode("utf-8")


st.title("🎯 Customer Intelligence")

st.caption(
    "RFM customer segmentation using Yeo-Johnson "
    "transformation, StandardScaler and K-Means."
)

st.caption("All monetary values are shown in British pounds sterling (GBP).")


try:
    customer_segments = load_customer_segments()

    cluster_profile = (
        load_customer_cluster_profile()
    )

    cluster_centres = (
        load_customer_cluster_centres()
    )

    segmentation_metrics = (
        load_customer_segmentation_metrics()
    )

    segmentation_metadata = (
        load_customer_segmentation_metadata()
    )

except FileNotFoundError as error:
    st.error(str(error))

    st.info(
        "Run the customer segmentation notebook "
        "and export its validated artifacts first."
    )

    st.stop()


# ---------------------------------------------------------
# Sidebar filters
# ---------------------------------------------------------

st.sidebar.header("Customer filters")

available_clusters = (
    customer_segments["ClusterName"]
    .dropna()
    .drop_duplicates()
    .tolist()
)

selected_clusters = st.sidebar.multiselect(
    "Customer segments",
    options=available_clusters,
    default=available_clusters,
)

customer_search = st.sidebar.text_input(
    "Search CustomerID",
    value="",
    placeholder="For example: 18102",
)

filtered_customers = (
    customer_segments.loc[
        customer_segments[
            "ClusterName"
        ].isin(selected_clusters)
    ]
    .copy()
)

if customer_search.strip():
    filtered_customers = (
        filtered_customers.loc[
            filtered_customers[
                "CustomerID"
            ]
            .astype("string")
            .str.contains(
                customer_search.strip(),
                regex=False,
                na=False,
            )
        ]
    )


# ---------------------------------------------------------
# KPI cards
# ---------------------------------------------------------

total_customers = len(
    customer_segments
)

total_clusters = (
    customer_segments["Cluster"]
    .nunique()
)

sampled_silhouette = float(
    segmentation_metrics.get(
        "SampledSilhouetteScore",
        np.nan,
    )
)

vip_profile = cluster_profile.loc[
    cluster_profile[
        "ClusterName"
    ].eq("VIP / Strategic")
]

vip_revenue_share = (
    float(
        vip_profile[
            "RevenueSharePercent"
        ].iloc[0]
    )
    if not vip_profile.empty
    else np.nan
)

kpi_1, kpi_2, kpi_3, kpi_4 = st.columns(4)

kpi_1.metric(
    "Segmented customers",
    f"{total_customers:,}",
)

kpi_2.metric(
    "Customer segments",
    f"{total_clusters}",
)

kpi_3.metric(
    "Silhouette score",
    f"{sampled_silhouette:.4f}",
)

kpi_4.metric(
    "VIP revenue share",
    f"{vip_revenue_share:.2f}%",
)


# ---------------------------------------------------------
# Customer and revenue shares
# ---------------------------------------------------------

st.subheader("Customer and revenue concentration")

share_data = (
    cluster_profile[
        [
            "ClusterName",
            "CustomerSharePercent",
            "RevenueSharePercent",
        ]
    ]
    .melt(
        id_vars="ClusterName",
        var_name="ShareType",
        value_name="Percent",
    )
)

share_data["ShareType"] = (
    share_data["ShareType"]
    .replace(
        {
            "CustomerSharePercent": (
                "Customer share"
            ),
            "RevenueSharePercent": (
                "Revenue share"
            ),
        }
    )
)

share_figure = px.bar(
    share_data,
    x="ClusterName",
    y="Percent",
    color="ShareType",
    barmode="group",
    text_auto=".1f",
    labels={
        "ClusterName": "Customer segment",
        "Percent": "Share (%)",
        "ShareType": "Measure",
    },
    color_discrete_map={
        "Customer share": "#5DADE2",
        "Revenue share": "#F5B041",
    },
)

share_figure.update_traces(
    textposition="outside"
)

share_figure.update_layout(
    legend_title_text="",
    xaxis_title="",
)

share_figure.update_yaxes(
    ticksuffix="%"
)

st.plotly_chart(
    share_figure,
    width="stretch",
)


# ---------------------------------------------------------
# RFM cluster profile
# ---------------------------------------------------------

st.subheader("RFM profile by segment")

chart_1, chart_2, chart_3 = st.columns(3)

recency_figure = px.bar(
    cluster_profile,
    x="ClusterName",
    y="AverageRecency",
    color="ClusterName",
    color_discrete_map=CLUSTER_COLORS,
    labels={
        "ClusterName": "",
        "AverageRecency": "Average recency (days)",
    },
    text_auto=".0f",
)

recency_figure.update_layout(
    showlegend=False
)

chart_1.plotly_chart(
    recency_figure,
    width="stretch",
)

frequency_figure = px.bar(
    cluster_profile,
    x="ClusterName",
    y="AverageFrequency",
    color="ClusterName",
    color_discrete_map=CLUSTER_COLORS,
    labels={
        "ClusterName": "",
        "AverageFrequency": "Average orders",
    },
    text_auto=".1f",
)

frequency_figure.update_layout(
    showlegend=False
)

chart_2.plotly_chart(
    frequency_figure,
    width="stretch",
)

monetary_figure = px.bar(
    cluster_profile,
    x="ClusterName",
    y="AverageNetMonetary",
    color="ClusterName",
    color_discrete_map=CLUSTER_COLORS,
    labels={
        "ClusterName": "",
        "AverageNetMonetary": (
            "Average net revenue"
        ),
    },
    text_auto=".2s",
)

monetary_figure.update_layout(
    showlegend=False
)

chart_3.plotly_chart(
    monetary_figure,
    width="stretch",
)


# ---------------------------------------------------------
# Customer distribution
# ---------------------------------------------------------

st.subheader("Customer distribution")

scatter_data = customer_segments.loc[
    customer_segments["Frequency"].gt(0)
    & customer_segments["Monetary"].gt(0)
].copy()

customer_scatter = px.scatter(
    scatter_data,
    x="Frequency",
    y="Monetary",
    color="ClusterName",
    color_discrete_map=CLUSTER_COLORS,
    hover_data={
        "CustomerID": True,
        "Recency": True,
        "Frequency": ":,.0f",
        "Monetary": ":,.2f",
        "AverageOrderValue": ":,.2f",
        "CancellationRatePercent": ":.2f",
    },
    log_x=True,
    log_y=True,
    opacity=0.55,
    labels={
        "Frequency": "Orders — logarithmic scale",
        "Monetary": (
            "Net monetary value — logarithmic scale"
        ),
        "ClusterName": "Customer segment",
    },
)

customer_scatter.update_layout(
    legend_title_text=""
)

st.plotly_chart(
    customer_scatter,
    width="stretch",
)

st.caption(
    "The logarithmic axes make the highly skewed "
    "customer-value distribution easier to interpret."
)


# ---------------------------------------------------------
# Business interpretation
# ---------------------------------------------------------

st.subheader("Recommended business actions")

recommendation_1, recommendation_2, recommendation_3 = (
    st.columns(3)
)

with recommendation_1:
    st.markdown(
        """
        **Inactive / Low Frequency**

        - Run targeted win-back campaigns.
        - Use low-cost reactivation offers.
        - Monitor customers with historically high value.
        """
    )

with recommendation_2:
    st.markdown(
        """
        **Active Core**

        - Strengthen loyalty and retention.
        - Recommend complementary products.
        - Encourage higher order frequency.
        """
    )

with recommendation_3:
    st.markdown(
        """
        **VIP / Strategic**

        - Provide dedicated account support.
        - Monitor customer concentration risk.
        - Protect service quality and availability.
        """
    )


# ---------------------------------------------------------
# Customer table
# ---------------------------------------------------------

st.subheader("Customer explorer")

st.write(
    f"Showing **{len(filtered_customers):,}** customers."
)

display_columns = [
    "CustomerID",
    "ClusterName",
    "Recency",
    "Frequency",
    "Monetary",
    "GrossMonetary",
    "AverageOrderValue",
    "UnitsPurchased",
    "UniqueProducts",
    "CancellationRatePercent",
]

customer_table = (
    filtered_customers[
        display_columns
    ]
    .sort_values(
        "Monetary",
        ascending=False,
    )
)

st.dataframe(
    customer_table,
    width="stretch",
    hide_index=True,
    column_config={
        "CustomerID": st.column_config.NumberColumn(
            "Customer ID",
            format="%d",
        ),
        "Recency": st.column_config.NumberColumn(
            "Recency (days)",
            format="%d",
        ),
        "Frequency": st.column_config.NumberColumn(
            "Orders",
            format="%d",
        ),
        "Monetary": st.column_config.NumberColumn(
            "Net monetary",
            format="%.2f",
        ),
        "GrossMonetary": st.column_config.NumberColumn(
            "Gross monetary",
            format="%.2f",
        ),
        "AverageOrderValue": (
            st.column_config.NumberColumn(
                "Average order value",
                format="%.2f",
            )
        ),
        "CancellationRatePercent": (
            st.column_config.NumberColumn(
                "Cancellation rate",
                format="%.2f%%",
            )
        ),
    },
)

st.download_button(
    label="Download filtered customers",
    data=prepare_customer_download(
        customer_table
    ),
    file_name="retailiq_customer_segments.csv",
    mime="text/csv",
)


# ---------------------------------------------------------
# Technical details
# ---------------------------------------------------------

with st.expander(
    "Model details"
):
    st.json(
        segmentation_metadata
    )

    st.markdown(
        "**Cluster centres in original RFM units**"
    )

    st.dataframe(
        cluster_centres,
        width="stretch",
        hide_index=True,
    )