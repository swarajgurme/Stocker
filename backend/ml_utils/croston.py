"""
Croston's Method implementation for intermittent and slow-moving materials demand forecasting.
Decomposes demand size and demand interval using exponential smoothing.
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, List


def fit_predict_croston(
    sales_series: pd.Series,
    forecast_days: int = 30,
    alpha: float = 0.1
) -> Dict[str, Any]:
    """
    Croston's Method for Intermittent / Slow-Moving Materials Demand Forecasting.

    Args:
        sales_series: Historical pandas Series of daily demand.
        forecast_days: Horizon forecast length in days.
        alpha: Exponential smoothing factor (0 < alpha < 1).

    Returns:
        Dict containing predicted values, bounds, and metrics.
    """
    values = sales_series.values if hasattr(sales_series, 'values') else np.array(sales_series)
    nonzero_indices = np.where(values > 0)[0]

    if len(nonzero_indices) == 0:
        pred = np.zeros(forecast_days)
        return {
            "predictions": pred.tolist(),
            "lower_bound": pred.tolist(),
            "upper_bound": (pred + 0.5).tolist(),
            "mean_demand": 0.0,
            "demand_size": 0.0,
            "demand_interval": 0.0,
        }

    # Initialize demand size (z) and period interval (p)
    z = float(values[nonzero_indices[0]])
    p = float(nonzero_indices[0] + 1) if nonzero_indices[0] > 0 else 1.0
    q = 1  # count of periods since last non-zero demand

    for i in range(1, len(values)):
        if values[i] > 0:
            z = alpha * float(values[i]) + (1.0 - alpha) * z
            p = alpha * float(q) + (1.0 - alpha) * p
            q = 1
        else:
            q += 1

    # Croston point forecast rate per period
    demand_rate = z / p if p > 0 else 0.0
    std_dev = float(np.std(values)) if len(values) > 1 else demand_rate * 0.5

    predictions = np.full(forecast_days, round(demand_rate, 2))
    lower = np.maximum(0, predictions - round(1.28 * std_dev * 0.3, 2))
    upper = predictions + round(1.28 * std_dev * 0.5, 2)

    return {
        "predictions": predictions.tolist(),
        "lower_bound": lower.round(2).tolist(),
        "upper_bound": upper.round(2).tolist(),
        "mean_demand": float(round(demand_rate, 3)),
        "demand_size": float(round(z, 2)),
        "demand_interval": float(round(p, 2)),
    }
