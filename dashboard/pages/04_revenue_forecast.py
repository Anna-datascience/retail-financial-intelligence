from pathlib import Path
import sys

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
import pandas as pd
import streamlit as st


# --------------------------------------------------
# Project imports
# --------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dashboard.utils.data_loader import (  # noqa: E402
    load_forecast_metadata,
    load_forecast_model_comparison,
    load_forecast_test_predictions,
    load_future_revenue_forecast,
)


# --------------------------------------------------
# Load and validate artifacts
# --------------------------------------------------

try:
    forecast_comparison = load_forecast_model_comparison()
    test_predictions = load_forecast_test_predictions()
    future_forecast = load_future_revenue_forecast()
    forecast_metadata = load_forecast_metadata()
except (FileNotFoundError, KeyError, ValueError) as error:
    st.error(f"Revenue-forecasting artifacts could not be loaded: {error}")
    st.stop()

if forecast_comparison.empty or test_predictions.empty or future_forecast.empty:
    st.error("One or more forecasting artifacts are empty.")
    st.stop()

forecast_comparison = (
    forecast_comparison.sort_values("WAPERank").reset_index(drop=True)
)

expected_test_observations = int(
    forecast_metadata.get("test_observations", len(test_predictions))
)

if len(test_predictions) != expected_test_observations:
    st.error(
        "Forecast artifact mismatch: metadata expects "
        f"{expected_test_observations} test rows, but the prediction file "
        f"contains {len(test_predictions)} rows."
    )
    st.stop()

selected_model = forecast_metadata.get(
    "selected_model", forecast_comparison.iloc[0]["Model"]
)
comparison_winner = forecast_comparison.iloc[0]["Model"]

if selected_model != comparison_winner:
    st.error(
        "The selected forecast model does not match the model-comparison winner."
    )
    st.stop()


# --------------------------------------------------
# Helpers and base metrics
# --------------------------------------------------

def format_pounds(value):
    return f"£{float(value):,.2f}"


def pounds_axis(value, position):
    del position
    if abs(value) >= 1_000_000:
        return f"£{value / 1_000_000:.1f}m"
    if abs(value) >= 1_000:
        return f"£{value / 1_000:.0f}k"
    return f"£{value:,.0f}"


selected_model_row = forecast_comparison.loc[
    forecast_comparison["Model"].eq(selected_model)
].iloc[0]

baseline_rows = forecast_comparison.loc[
    forecast_comparison["Model"].eq("SameWeekday4WeekAverage")
]

if baseline_rows.empty:
    wape_improvement = float(
        forecast_metadata.get("wape_improvement_over_baseline_percent", 0)
    )
else:
    baseline_wape = float(baseline_rows.iloc[0]["WAPEPercent"])
    selected_wape = float(selected_model_row["WAPEPercent"])
    wape_improvement = (baseline_wape - selected_wape) / baseline_wape * 100


# --------------------------------------------------
# Sidebar filters
# --------------------------------------------------

test_series_columns = {
    "Actual revenue": "ActualRevenue",
    "Same-weekday baseline": "BaselinePrediction",
    "Tuned XGBoost": "XGBoostPrediction",
    "LSTM": "LSTMPrediction",
}

test_line_styles = {
    "Actual revenue": {"color": "black", "linewidth": 2.2, "alpha": 1.0},
    "Same-weekday baseline": {
        "color": "#3B82F6",
        "linewidth": 1.5,
        "alpha": 0.85,
    },
    "Tuned XGBoost": {"color": "#F97316", "linewidth": 1.8, "alpha": 1.0},
    "LSTM": {"color": "#10B981", "linewidth": 1.3, "alpha": 0.75},
}

metric_options = {
    "WAPE (%)": "WAPEPercent",
    "SMAPE (%)": "SMAPEPercent",
    "MAE (£)": "MAE",
    "RMSE (£)": "RMSE",
}

with st.sidebar:
    st.header("Forecast filters")

    selected_test_series = st.multiselect(
        "Test-period lines",
        options=list(test_series_columns),
        default=[
            "Actual revenue",
            "Same-weekday baseline",
            "Tuned XGBoost",
        ],
    )

    test_date_selection = st.date_input(
        "Test date range",
        value=(
            test_predictions["ForecastDate"].min().date(),
            test_predictions["ForecastDate"].max().date(),
        ),
        min_value=test_predictions["ForecastDate"].min().date(),
        max_value=test_predictions["ForecastDate"].max().date(),
    )

    forecast_horizon = st.slider(
        "Future forecast horizon",
        min_value=1,
        max_value=int(future_forecast["ForecastHorizonDay"].max()),
        value=int(future_forecast["ForecastHorizonDay"].max()),
        step=1,
        format="%d days",
    )

    comparison_metric_label = st.selectbox(
        "Model-comparison metric",
        options=list(metric_options),
        index=0,
    )

    show_uncertainty = st.checkbox("Show uncertainty range", value=True)
    st.caption("Filters change dashboard displays only; models are not retrained.")

if not selected_test_series:
    selected_test_series = ["Actual revenue", "Tuned XGBoost"]

if isinstance(test_date_selection, (tuple, list)) and len(test_date_selection) == 2:
    selected_test_start = pd.Timestamp(test_date_selection[0])
    selected_test_end = pd.Timestamp(test_date_selection[1])
else:
    selected_test_start = test_predictions["ForecastDate"].min()
    selected_test_end = test_predictions["ForecastDate"].max()

filtered_test_predictions = test_predictions.loc[
    test_predictions["ForecastDate"].between(selected_test_start, selected_test_end)
].copy()

filtered_future_forecast = future_forecast.loc[
    future_forecast["ForecastHorizonDay"].le(forecast_horizon)
].copy()

if filtered_test_predictions.empty or filtered_future_forecast.empty:
    st.warning("The selected filters returned no forecast observations.")
    st.stop()

future_total_revenue = filtered_future_forecast["PredictedRevenue"].sum()
future_average_revenue = filtered_future_forecast["PredictedRevenue"].mean()
peak_forecast_row = filtered_future_forecast.loc[
    filtered_future_forecast["PredictedRevenue"].idxmax()
]
peak_forecast_revenue = float(peak_forecast_row["PredictedRevenue"])
peak_forecast_date = peak_forecast_row["ForecastDate"].strftime("%d %b %Y")
test_start = filtered_test_predictions["ForecastDate"].min().strftime("%d %b %Y")
test_end = filtered_test_predictions["ForecastDate"].max().strftime("%d %b %Y")
future_start = filtered_future_forecast["ForecastDate"].min().strftime(
    "%d %b %Y"
)
future_end = filtered_future_forecast["ForecastDate"].max().strftime("%d %b %Y")


# --------------------------------------------------
# Page header and KPIs
# --------------------------------------------------

st.title("📈 Revenue Forecasting")
st.caption(
    "Daily revenue forecasting, model evaluation and financial outlook. "
    "All monetary values are shown in British pounds sterling (GBP, £)."
)

metric_columns = st.columns(5)
with metric_columns[0]:
    st.metric(
        "Selected model",
        "XGBoost",
        help=f"Full model name: {selected_model}"
    )

    st.caption(selected_model)
metric_columns[1].metric(
    "Test WAPE", f"{float(selected_model_row['WAPEPercent']):.2f}%"
)
metric_columns[2].metric(
    "Improvement vs baseline", f"{wape_improvement:.2f}%"
)
metric_columns[3].metric(
    f"{forecast_horizon}-day forecast", format_pounds(future_total_revenue)
)
metric_columns[4].metric(
    "Average forecast per day", format_pounds(future_average_revenue)
)

backtest_tab, future_tab, details_tab = st.tabs(
    ["Model evaluation", "Future forecast", "Methodology"]
)
st.set_page_config(
    page_title="Revenue Forecasting | RetailIQ",
    page_icon="📈",
    layout="wide",
)

# --------------------------------------------------
# Model evaluation
# --------------------------------------------------

with backtest_tab:
    st.subheader("Final test-period performance")
    st.write(
        f"Displaying **{len(filtered_test_predictions):,} days**, from "
        f"**{test_start}** to **{test_end}**. The complete holdout contains "
        f"{len(test_predictions):,} days."
    )

    st.dataframe(
        forecast_comparison,
        hide_index=True,
        width="stretch",
        column_config={
            "Observations": st.column_config.NumberColumn(
                "Observations", format="%d"
            ),
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
            "WAPERank": st.column_config.NumberColumn("WAPE rank", format="%d"),
        },
    )

    st.subheader("Actual versus predicted revenue")
    fig, ax = plt.subplots(figsize=(15, 6))

    for series_label in selected_test_series:
        ax.plot(
            filtered_test_predictions["ForecastDate"],
            filtered_test_predictions[test_series_columns[series_label]],
            label=series_label,
            **test_line_styles[series_label],
        )

    ax.set_title("Daily Revenue Forecast — Selected Test Period")
    ax.set_xlabel("Date")
    ax.set_ylabel("Daily Revenue (£)")
    ax.yaxis.set_major_formatter(FuncFormatter(pounds_axis))
    ax.xaxis.set_major_locator(mdates.WeekdayLocator(interval=2))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
    ax.legend(loc="upper left", ncol=2, frameon=True)
    ax.grid(alpha=0.25)
    fig.autofmt_xdate()
    fig.tight_layout()
    st.pyplot(fig, width="stretch")
    plt.close(fig)

    comparison_metric = metric_options[comparison_metric_label]
    comparison_plot = forecast_comparison.sort_values(comparison_metric).copy()
    bar_colours = [
        "#F97316" if model == selected_model else "#94A3B8"
        for model in comparison_plot["Model"]
    ]

    st.subheader(f"Model comparison: {comparison_metric_label}")
    fig, ax = plt.subplots(figsize=(10, 4.5))
    bars = ax.barh(
        comparison_plot["Model"],
        comparison_plot[comparison_metric],
        color=bar_colours,
    )

    if comparison_metric in {"MAE", "RMSE"}:
        bar_labels = [
            format_pounds(value) for value in comparison_plot[comparison_metric]
        ]
    else:
        bar_labels = [
            f"{value:.2f}%" for value in comparison_plot[comparison_metric]
        ]

    ax.bar_label(bars, labels=bar_labels, padding=4)
    ax.set_xlabel(comparison_metric_label)
    ax.set_ylabel("Model")
    ax.grid(axis="x", alpha=0.25)
    fig.tight_layout()
    st.pyplot(fig, width="stretch")
    plt.close(fig)

    st.success(
        f"{selected_model} is the selected model and reduced WAPE by "
        f"approximately {wape_improvement:.2f}% relative to the business baseline."
    )


# --------------------------------------------------
# Future forecast
# --------------------------------------------------

with future_tab:
    st.subheader(f"Future {forecast_horizon}-day revenue forecast")
    st.write(f"The displayed forecast covers **{future_start}** to **{future_end}**.")

    future_metrics = st.columns(3)
    future_metrics[0].metric("Forecast revenue", format_pounds(future_total_revenue))
    future_metrics[1].metric(
        "Average daily revenue", format_pounds(future_average_revenue)
    )
    future_metrics[2].metric(
        f"Peak forecast · {peak_forecast_date}",
        format_pounds(peak_forecast_revenue),
    )

    forecast_dates = filtered_future_forecast["ForecastDate"].to_numpy()
    lower_estimate = filtered_future_forecast["LowerRevenueEstimate"].to_numpy(
        dtype=float
    )
    upper_estimate = filtered_future_forecast["UpperRevenueEstimate"].to_numpy(
        dtype=float
    )
    predicted_revenue = filtered_future_forecast["PredictedRevenue"].to_numpy(
        dtype=float
    )

    fig, ax = plt.subplots(figsize=(15, 6))
    if show_uncertainty:
        ax.fill_between(
            forecast_dates,
            lower_estimate,
            upper_estimate,
            color="#FDBA74",
            alpha=0.35,
            label="10th–90th percentile estimate",
        )

    ax.plot(
        forecast_dates,
        predicted_revenue,
        color="#F97316",
        linewidth=2.4,
        marker="o",
        markersize=3.5,
        label="XGBoost forecast",
    )
    ax.set_title(f"Future {forecast_horizon}-Day Daily Revenue Forecast")
    ax.set_xlabel("Forecast date")
    ax.set_ylabel("Predicted Revenue (£)")
    ax.yaxis.set_major_formatter(FuncFormatter(pounds_axis))
    ax.xaxis.set_major_locator(mdates.WeekdayLocator(interval=1))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
    ax.legend(loc="upper left", frameon=True)
    ax.grid(alpha=0.25)
    fig.autofmt_xdate()
    fig.tight_layout()
    st.pyplot(fig, width="stretch")
    plt.close(fig)

    st.caption(
        "The range uses the 10th and 90th percentiles of validation residuals. "
        "It is an empirical uncertainty estimate, not a formal confidence interval."
    )

    st.dataframe(
        filtered_future_forecast,
        hide_index=True,
        width="stretch",
        column_config={
            "ForecastDate": st.column_config.DateColumn(
                "Forecast date", format="DD MMM YYYY"
            ),
            "ForecastHorizonDay": st.column_config.NumberColumn(
                "Forecast day", format="%d"
            ),
            "PredictedRevenue": st.column_config.NumberColumn(
                "Predicted revenue (£)", format="£%.2f"
            ),
            "LowerRevenueEstimate": st.column_config.NumberColumn(
                "Lower estimate (£)", format="£%.2f"
            ),
            "UpperRevenueEstimate": st.column_config.NumberColumn(
                "Upper estimate (£)", format="£%.2f"
            ),
        },
    )

    st.download_button(
        label="Download displayed forecast",
        data=filtered_future_forecast.to_csv(index=False).encode("utf-8"),
        file_name=f"retailiq_{forecast_horizon}_day_revenue_forecast.csv",
        mime="text/csv",
    )


# --------------------------------------------------
# Methodology
# --------------------------------------------------

with details_tab:
    st.subheader("Forecasting methodology")
    st.markdown(
        """
        - Forecast grain: daily revenue
        - Validation start: 1 June 2011
        - Final test period: 1 September–30 November 2011
        - Partial December 2011 excluded from formal evaluation
        - Models compared: same-weekday baseline, XGBoost and LSTM
        - Primary selection metric: WAPE
        - Future strategy: recursive multi-step forecasting
        - Currency: British pounds sterling (GBP)

        The same-weekday method remains the business baseline. XGBoost was
        selected because it achieved the best WAPE, MAE, RMSE and absolute
        bias on the final 91-day holdout. Recursive uncertainty can increase
        as the forecast horizon becomes longer.
        """
    )

    with st.expander("View forecast metadata"):
        st.json(forecast_metadata)

    st.download_button(
        label="Download model comparison",
        data=forecast_comparison.to_csv(index=False).encode("utf-8"),
        file_name="retailiq_forecast_model_comparison.csv",
        mime="text/csv",
    )
