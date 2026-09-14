"""RetailIQ product and market-basket dashboard."""

from pathlib import Path
import sys

import numpy as np
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
    load_market_basket_rules,
    load_market_basket_summary,
    load_product_lifecycle,
)


st.set_page_config(
    page_title="Product and Basket | RetailIQ",
    page_icon="🛒",
    layout="wide",
)


ABC_COLORS = {
    "A": "#E74C3C",
    "B": "#F5B041",
    "C": "#5DADE2",
}


@st.cache_data(show_spinner=False)
def prepare_download(
    dataframe: pd.DataFrame,
) -> bytes:
    return dataframe.to_csv(
        index=False
    ).encode("utf-8")


st.title("🛒 Product and Basket Intelligence")

st.caption(
    "Product performance, lifecycle monitoring and "
    "cross-selling recommendations."
)

st.caption("All monetary values are shown in British pounds sterling (GBP).")

try:
    product_lifecycle = (
        load_product_lifecycle()
    )

    basket_rules = (
        load_market_basket_rules()
    )

except (FileNotFoundError, KeyError) as error:
    st.error(str(error))
    st.stop()


try:
    basket_summary = (
        load_market_basket_summary()
    )

except FileNotFoundError:
    basket_summary = pd.DataFrame()


# ---------------------------------------------------------
# Product lifecycle classification
# ---------------------------------------------------------

product_lifecycle = product_lifecycle.copy()

product_lifecycle[
    "LifecycleStatus"
] = np.where(
    product_lifecycle[
        "DaysSinceLastSale"
    ].ge(180)
    | product_lifecycle["Orders"].le(2),
    "Inactive / Low Frequency",
    "Active",
)


# ---------------------------------------------------------
# Sidebar filters
# ---------------------------------------------------------

st.sidebar.header("Product filters")

abc_classes = sorted(
    product_lifecycle[
        "ABCClass"
    ]
    .dropna()
    .unique()
    .tolist()
)

selected_abc_classes = st.sidebar.multiselect(
    "ABC classes",
    options=abc_classes,
    default=abc_classes,
)

lifecycle_options = [
    "Active",
    "Inactive / Low Frequency",
]

selected_lifecycle = st.sidebar.multiselect(
    "Lifecycle status",
    options=lifecycle_options,
    default=lifecycle_options,
)

product_search = st.sidebar.text_input(
    "Search product",
    placeholder="Stock code or description",
)

st.sidebar.divider()

st.sidebar.header("Basket-rule filters")

minimum_confidence = st.sidebar.slider(
    "Minimum confidence",
    min_value=0.0,
    max_value=1.0,
    value=0.50,
    step=0.05,
)

minimum_lift = st.sidebar.number_input(
    "Minimum lift",
    min_value=1.0,
    value=1.20,
    step=0.10,
)

rule_search = st.sidebar.text_input(
    "Search basket rules",
    placeholder="Product name or stock code",
)


filtered_products = product_lifecycle.loc[
    product_lifecycle[
        "ABCClass"
    ].isin(selected_abc_classes)
    & product_lifecycle[
        "LifecycleStatus"
    ].isin(selected_lifecycle)
].copy()

if product_search.strip():
    product_search_mask = (
        filtered_products[
            "StockCodeNormalized"
        ]
        .astype("string")
        .str.contains(
            product_search.strip(),
            case=False,
            regex=False,
            na=False,
        )
        |
        filtered_products[
            "Description"
        ]
        .astype("string")
        .str.contains(
            product_search.strip(),
            case=False,
            regex=False,
            na=False,
        )
    )

    filtered_products = (
        filtered_products.loc[
            product_search_mask
        ]
    )


filtered_rules = basket_rules.loc[
    basket_rules["confidence"].ge(
        minimum_confidence
    )
    & basket_rules["lift"].ge(
        minimum_lift
    )
].copy()

if rule_search.strip():
    rule_search_mask = (
        filtered_rules[
            "AntecedentProducts"
        ]
        .astype("string")
        .str.contains(
            rule_search.strip(),
            case=False,
            regex=False,
            na=False,
        )
        |
        filtered_rules[
            "ConsequentProducts"
        ]
        .astype("string")
        .str.contains(
            rule_search.strip(),
            case=False,
            regex=False,
            na=False,
        )
    )

    filtered_rules = (
        filtered_rules.loc[
            rule_search_mask
        ]
    )


# ---------------------------------------------------------
# Executive KPIs
# ---------------------------------------------------------

total_products = (
    product_lifecycle[
        "StockCodeNormalized"
    ].nunique()
)

inactive_products = int(
    product_lifecycle[
        "LifecycleStatus"
    ]
    .eq("Inactive / Low Frequency")
    .sum()
)

total_revenue = (
    product_lifecycle["Revenue"].sum()
)

a_class_revenue = (
    product_lifecycle.loc[
        product_lifecycle[
            "ABCClass"
        ].eq("A"),
        "Revenue",
    ].sum()
)

a_class_revenue_share = (
    a_class_revenue / total_revenue * 100
    if total_revenue != 0
    else 0
)

median_confidence = (
    basket_rules["confidence"].median()
    * 100
)

st.subheader("Executive snapshot")

kpi_1, kpi_2, kpi_3, kpi_4 = st.columns(4)

kpi_1.metric(
    "Products analysed",
    f"{total_products:,}",
)

kpi_2.metric(
    "Inactive candidates",
    f"{inactive_products:,}",
    help=(
        "Products with at least 180 days since "
        "last sale or no more than two orders."
    ),
)

kpi_3.metric(
    "A-class revenue share",
    f"{a_class_revenue_share:.1f}%",
)

kpi_4.metric(
    "Median rule confidence",
    f"{median_confidence:.1f}%",
)


# ---------------------------------------------------------
# ABC analysis
# ---------------------------------------------------------

st.subheader("ABC product performance")

abc_summary = (
    product_lifecycle
    .groupby(
        "ABCClass",
        observed=True,
    )
    .agg(
        Products=(
            "StockCodeNormalized",
            "nunique",
        ),
        Revenue=("Revenue", "sum"),
        UnitsSold=("UnitsSold", "sum"),
        Orders=("Orders", "sum"),
    )
    .reset_index()
    .sort_values("ABCClass")
)

abc_1, abc_2 = st.columns(2)

abc_revenue_chart = px.bar(
    abc_summary,
    x="ABCClass",
    y="Revenue",
    color="ABCClass",
    color_discrete_map=ABC_COLORS,
    text_auto=".3s",
    labels={
        "ABCClass": "ABC class",
        "Revenue": "Revenue",
    },
)

abc_revenue_chart.update_layout(
    showlegend=False
)

abc_1.plotly_chart(
    abc_revenue_chart,
    width="stretch",
)

abc_product_chart = px.bar(
    abc_summary,
    x="ABCClass",
    y="Products",
    color="ABCClass",
    color_discrete_map=ABC_COLORS,
    text_auto=True,
    labels={
        "ABCClass": "ABC class",
        "Products": "Number of products",
    },
)

abc_product_chart.update_layout(
    showlegend=False
)

abc_2.plotly_chart(
    abc_product_chart,
    width="stretch",
)


# ---------------------------------------------------------
# Top products
# ---------------------------------------------------------

st.subheader("Highest-revenue products")

top_products = (
    product_lifecycle
    .nlargest(
        15,
        "Revenue"
    )
    .sort_values(
        "Revenue",
        ascending=True,
    )
)

top_product_chart = px.bar(
    top_products,
    x="Revenue",
    y="Description",
    orientation="h",
    color="ABCClass",
    color_discrete_map=ABC_COLORS,
    hover_data={
        "StockCodeNormalized": True,
        "UnitsSold": ":,.0f",
        "Orders": ":,.0f",
        "DaysSinceLastSale": ":,.0f",
    },
    labels={
        "Description": "",
        "Revenue": "Revenue",
        "ABCClass": "ABC class",
    },
)

st.plotly_chart(
    top_product_chart,
    width="stretch",
)


# ---------------------------------------------------------
# Product lifecycle
# ---------------------------------------------------------

st.subheader("Product lifecycle monitor")

lifecycle_summary = (
    product_lifecycle
    .groupby(
        [
            "ABCClass",
            "LifecycleStatus",
        ],
        observed=True,
    )
    .size()
    .reset_index(
        name="Products"
    )
)

lifecycle_chart = px.bar(
    lifecycle_summary,
    x="ABCClass",
    y="Products",
    color="LifecycleStatus",
    barmode="group",
    text_auto=True,
    labels={
        "ABCClass": "ABC class",
        "Products": "Products",
        "LifecycleStatus": "Lifecycle status",
    },
    color_discrete_map={
        "Active": "#27AE60",
        "Inactive / Low Frequency": "#95A5A6",
    },
)

lifecycle_chart.update_layout(
    legend_title_text=""
)

st.plotly_chart(
    lifecycle_chart,
    width="stretch",
)

st.warning(
    "Inactive products are review candidates, not confirmed "
    "discontinued products. Seasonal and catalogue context "
    "must be considered before removal."
)


# ---------------------------------------------------------
# Market-basket rules
# ---------------------------------------------------------

st.subheader("Cross-selling opportunities")

st.write(
    f"Showing **{len(filtered_rules):,}** association rules "
    f"with confidence ≥ {minimum_confidence:.0%} and "
    f"lift ≥ {minimum_lift:.2f}."
)

rule_plot_data = (
    filtered_rules
    .nlargest(
        300,
        "lift"
    )
    .copy()
)

if not rule_plot_data.empty:
    basket_chart = px.scatter(
        rule_plot_data,
        x="support",
        y="confidence",
        size="BasketCount",
        color="lift",
        color_continuous_scale="Viridis",
        hover_data={
            "AntecedentProducts": True,
            "ConsequentProducts": True,
            "support": ":.3%",
            "confidence": ":.1%",
            "lift": ":.2f",
            "BasketCount": ":,.0f",
        },
        labels={
            "support": "Support",
            "confidence": "Confidence",
            "lift": "Lift",
            "BasketCount": "Basket count",
        },
        size_max=30,
    )

    basket_chart.update_xaxes(
        tickformat=".1%"
    )

    basket_chart.update_yaxes(
        tickformat=".0%"
    )

    st.plotly_chart(
        basket_chart,
        width="stretch",
    )

else:
    st.info(
        "No rules meet the selected filters."
    )


# ---------------------------------------------------------
# Rules table
# ---------------------------------------------------------

rule_table = filtered_rules[
    [
        "AntecedentProducts",
        "ConsequentProducts",
        "support",
        "confidence",
        "lift",
        "BasketCount",
    ]
].copy()

rule_table["SupportPercent"] = (
    rule_table["support"] * 100
)

rule_table["ConfidencePercent"] = (
    rule_table["confidence"] * 100
)

rule_table = (
    rule_table[
        [
            "AntecedentProducts",
            "ConsequentProducts",
            "SupportPercent",
            "ConfidencePercent",
            "lift",
            "BasketCount",
        ]
    ]
    .sort_values(
        [
            "lift",
            "ConfidencePercent",
        ],
        ascending=False,
    )
)

st.dataframe(
    rule_table,
    width="stretch",
    hide_index=True,
    column_config={
        "AntecedentProducts": (
            "If basket contains"
        ),
        "ConsequentProducts": (
            "Recommend"
        ),
        "SupportPercent": (
            st.column_config.NumberColumn(
                "Support",
                format="%.2f%%",
            )
        ),
        "ConfidencePercent": (
            st.column_config.NumberColumn(
                "Confidence",
                format="%.1f%%",
            )
        ),
        "lift": (
            st.column_config.NumberColumn(
                "Lift",
                format="%.2f",
            )
        ),
        "BasketCount": (
            st.column_config.NumberColumn(
                "Basket count",
                format="%d",
            )
        ),
    },
)


# ---------------------------------------------------------
# Business recommendations
# ---------------------------------------------------------

st.subheader("Recommended actions")

action_1, action_2, action_3 = st.columns(3)

with action_1:
    st.markdown(
        """
        **Protect A-class products**

        Prioritise stock availability and supplier reliability for
        products responsible for the largest revenue contribution.
        """
    )

with action_2:
    st.markdown(
        """
        **Review inactive products**

        Investigate low-frequency and long-inactive products before
        catalogue rationalisation or discontinuation.
        """
    )

with action_3:
    st.markdown(
        """
        **Apply basket recommendations**

        Use high-confidence, high-lift rules for bundles, cross-selling
        prompts and merchandising experiments.
        """
    )


# ---------------------------------------------------------
# Product explorer
# ---------------------------------------------------------

st.subheader("Product explorer")

product_table_columns = [
    "StockCodeNormalized",
    "Description",
    "ABCClass",
    "LifecycleStatus",
    "Revenue",
    "UnitsSold",
    "Orders",
    "FirstSale",
    "LastSale",
    "DaysSinceLastSale",
]

product_table = (
    filtered_products[
        product_table_columns
    ]
    .sort_values(
        "Revenue",
        ascending=False,
    )
)

st.write(
    f"Showing **{len(product_table):,}** products."
)

st.dataframe(
    product_table,
    width="stretch",
    hide_index=True,
    column_config={
        "StockCodeNormalized": "Stock code",
        "ABCClass": "ABC class",
        "LifecycleStatus": "Lifecycle status",
        "Revenue": (
            st.column_config.NumberColumn(
                "Revenue",
                format="%.2f",
            )
        ),
        "UnitsSold": (
            st.column_config.NumberColumn(
                "Units sold",
                format="%.0f",
            )
        ),
        "Orders": (
            st.column_config.NumberColumn(
                "Orders",
                format="%.0f",
            )
        ),
        "DaysSinceLastSale": (
            st.column_config.NumberColumn(
                "Days since last sale",
                format="%.0f",
            )
        ),
    },
)

download_1, download_2 = st.columns(2)

download_1.download_button(
    "Download filtered products",
    data=prepare_download(
        product_table
    ),
    file_name=(
        "retailiq_product_lifecycle.csv"
    ),
    mime="text/csv",
)

download_2.download_button(
    "Download filtered basket rules",
    data=prepare_download(
        rule_table
    ),
    file_name=(
        "retailiq_market_basket_rules.csv"
    ),
    mime="text/csv",
)


with st.expander(
    "Market-basket methodology"
):
    st.markdown(
        """
        - Final basket matrix: 34,497 invoices × 1,000 products.
        - Rules were screened using support, confidence and lift.
        - Confidence is directional.
        - Lift above 1 indicates positive association.
        - Association does not prove that one product causes another
          product to be purchased.
        """
    )

    if not basket_summary.empty:
        st.dataframe(
            basket_summary,
            width="stretch",
            hide_index=True,
        )