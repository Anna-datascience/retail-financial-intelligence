
## Forecasting Executive Summary

RetailIQ compared three daily revenue forecasting approaches:

1. A same-weekday four-week seasonal baseline
2. A tuned XGBoost regression model
3. A 30-day sequence LSTM model

The models were developed using chronological training and validation
periods and evaluated on the final complete test period from
September to November 2011. Partial December 2011 was excluded from
model evaluation.

The selected model was **Tuned XGBoost Raw Target**, based primarily
on the lowest test WAPE.

### Final Test Performance

| Model | MAE | RMSE | WAPE | SMAPE | Bias |
|---|---:|---:|---:|---:|---:|
| Same-weekday baseline | 12,068.30 | 16,978.48 | 31.14% | 33.97% | -12.42% |
| Tuned XGBoost | 9,800.32 | 14,121.72 | 25.29% | 51.34% | -2.68% |
| LSTM | 20,272.26 | 27,115.92 | 52.31% | 85.76% | -50.14% |

XGBoost changed WAPE by **18.79%**
relative to the seasonal baseline.

## Future Revenue Forecast

The final XGBoost configuration was refitted using all complete
historical observations through **30 November 2011**.

It generated a recursive 30-day forecast covering
**1–30 December 2011**.

- Total predicted revenue: **1,280,806.03**
- Average predicted daily revenue: **42,693.53**
- Forecast horizon: **30 days**
- Forecast strategy: **recursive multi-step forecasting**

## Business Recommendations

- Use the forecast as a rolling input for cash-flow, inventory and
  staffing planning.
- Refresh the forecast whenever new daily transactions become
  available.
- Compare actual and predicted revenue weekly to monitor forecast
  error and bias.
- Investigate unusually high or low forecast days before making
  purchasing or staffing decisions.
- Retain the seasonal baseline as a monitoring challenger because it
  provides a simple and transparent benchmark.
- Use the forecast range rather than relying only on the point
  prediction.

## Model Governance

XGBoost was selected only after comparison with a transparent
seasonal baseline and an LSTM benchmark. The LSTM was not selected
solely because it was more complex. This demonstrates that model
selection was based on out-of-sample evidence rather than model
complexity.

## Limitations

- The dataset contains approximately two years of historical
  transactions.
- Promotion, marketing, weather, inventory availability and public
  holiday information were unavailable.
- Large wholesale orders create occasional revenue spikes that are
  difficult to predict.
- The test evaluation is rolling one-day-ahead, whereas the future
  output is a recursive 30-day forecast.
- Recursive predictions accumulate uncertainty because later lag
  features contain earlier predictions.
- The 80% reference band is based on validation residuals and is not
  a fully calibrated probabilistic prediction interval.
- The forecast represents aggregate daily revenue and does not
  predict individual products, customers or invoices.
