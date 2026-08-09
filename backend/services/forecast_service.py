"""
Forecast Service
Machine learning service for time series forecasting
Supports Prophet, ARIMA, XGBoost; LSTM reserved for future builds
"""

import logging
from datetime import timedelta
from typing import Any, Dict, Optional, Tuple
import pandas as pd
import numpy as np

from prophet import Prophet

from config import get_config

logger = logging.getLogger(__name__)
config = get_config()


def _normalize_model_key(model_type: Any) -> str:
    if model_type is None:
        return "prophet"
    if hasattr(model_type, "value"):
        model_type = model_type.value
    s = str(model_type).strip().lower()
    if s == "auto":
        return "auto"
    if s == "lstm":
        raise ValueError(
            "LSTM forecasting is not enabled in this deployment. "
            "Use prophet, arima, or xgboost."
        )
    return s


class BaseForecaster:
    """Base class for forecasting models"""

    def __init__(self, model_type: str):
        self.model_type = model_type
        self.model = None
        self.metrics = {}

    def train(self, df: pd.DataFrame, **kwargs):
        raise NotImplementedError

    def predict(self, periods: int, **kwargs) -> pd.DataFrame:
        raise NotImplementedError

    def evaluate(self, actual: np.ndarray, predicted: np.ndarray) -> Dict[str, float]:
        from sklearn.metrics import mean_absolute_error, mean_squared_error

        mae = mean_absolute_error(actual, predicted)
        mse = mean_squared_error(actual, predicted)
        rmse = np.sqrt(mse)
        mask = actual != 0
        if np.any(mask):
            mape = np.mean(np.abs((actual[mask] - predicted[mask]) / actual[mask])) * 100
        else:
            mape = np.nan

        return {
            "mae": round(float(mae), 4),
            "rmse": round(float(rmse), 4),
            "mape": round(float(mape), 4) if not np.isnan(mape) else None,
        }


class ProphetForecaster(BaseForecaster):
    """Facebook Prophet forecaster"""

    def __init__(self, **prophet_kwargs):
        super().__init__("prophet")
        self.model = Prophet(
            interval_width=0.95,
            daily_seasonality=False,
            yearly_seasonality=True,
            weekly_seasonality=True,
            **prophet_kwargs,
        )

    def train(self, df: pd.DataFrame, **kwargs):
        df_fit = df.copy()
        df_fit["ds"] = pd.to_datetime(df_fit["ds"])
        self.model.fit(df_fit[["ds", "y"]])

    def predict(self, periods: int, freq: str = "D", **kwargs) -> pd.DataFrame:
        future = self.model.make_future_dataframe(periods=periods, freq=freq)
        forecast = self.model.predict(future)
        forecast["ds"] = pd.to_datetime(forecast["ds"])
        return forecast


class ARIMAForecaster(BaseForecaster):
    """ARIMA forecaster using statsmodels"""

    def __init__(self, order: Tuple[int, int, int] = (1, 1, 1)):
        super().__init__("arima")
        self.order = order
        self._last_hist_ts = None

    def train(self, df: pd.DataFrame, **kwargs):
        from statsmodels.tsa.arima.model import ARIMA

        df = df.copy()
        df["ds"] = pd.to_datetime(df["ds"])
        ts = df.set_index("ds")["y"].asfreq("D")
        ts = ts.interpolate(method="linear").bfill().ffill()
        self._last_hist_ts = ts.index.max()
        self.model_fit = ARIMA(ts, order=self.order)
        self.model = self.model_fit.fit()

    def predict(self, periods: int, **kwargs) -> pd.DataFrame:
        forecast_res = self.model.get_forecast(steps=periods)
        pred_mean = forecast_res.predicted_mean
        conf = forecast_res.conf_int(alpha=0.05)
        start = pd.to_datetime(self._last_hist_ts) + pd.Timedelta(days=1)
        dates = pd.date_range(start=start, periods=periods, freq="D")
        yhat = pred_mean.values[:periods]
        lower = (
            conf.iloc[:periods, 0].values
            if conf is not None and len(conf) >= periods
            else yhat * 0.9
        )
        upper = (
            conf.iloc[:periods, 1].values
            if conf is not None and len(conf) >= periods
            else yhat * 1.1
        )
        return pd.DataFrame(
            {"ds": dates, "yhat": yhat, "yhat_lower": lower, "yhat_upper": upper}
        )


class XGBoostForecaster(BaseForecaster):
    """Gradient boosted lag model for sequential forecasting"""

    def __init__(self, lags: int = 7, n_estimators: int = 100):
        super().__init__("xgboost")
        self.lags = lags
        self.n_estimators = n_estimators
        self.model = None
        self._window: Optional[np.ndarray] = None
        self._last_hist = None

    def train(self, df: pd.DataFrame, **kwargs):
        import xgboost as xgb

        y = df.sort_values("ds")["y"].astype(float).values
        n = len(y)
        if n < self.lags + 5:
            raise ValueError(f"Need at least {self.lags + 5} points for XGBoost; got {n}")
        X_rows, Y_rows = [], []
        for i in range(self.lags, n):
            X_rows.append(y[i - self.lags : i])
            Y_rows.append(y[i])
        X_m = np.array(X_rows)
        Y_m = np.array(Y_rows)
        self.model = xgb.XGBRegressor(
            n_estimators=self.n_estimators,
            max_depth=5,
            learning_rate=0.08,
            random_state=42,
            n_jobs=0,
        )
        self.model.fit(X_m, Y_m)
        self._window = np.array(y[-self.lags :], dtype=float)
        self._last_hist = pd.to_datetime(df["ds"].max())

    def predict(self, periods: int, **kwargs) -> pd.DataFrame:
        if self.model is None or self._window is None or self._last_hist is None:
            raise ValueError("XGBoost model not trained")

        preds: list = []
        window = list(self._window)
        for _ in range(periods):
            feat = np.array(window[-self.lags :]).reshape(1, -1)
            p = float(self.model.predict(feat)[0])
            preds.append(p)
            window.append(p)

        start = pd.to_datetime(self._last_hist).normalize() + pd.Timedelta(days=1)
        dates = pd.date_range(start=start, periods=periods, freq="D")
        arr = np.array(preds)
        volatility = np.std(window[: self.lags]) or (np.mean(np.abs(arr)) * 0.05 + 1e-6)
        lower = arr - 1.96 * volatility
        upper = arr + 1.96 * volatility
        return pd.DataFrame(
            {"ds": dates, "yhat": arr, "yhat_lower": lower, "yhat_upper": upper}
        )


class LSTMForecaster(BaseForecaster):
    """Reserved — not bundled in production image"""

    def __init__(self, lookback: int = 30):
        super().__init__("lstm")
        self.lookback = lookback

    def train(self, df: pd.DataFrame, **kwargs):
        raise ValueError(
            "LSTM is not enabled. Install TensorFlow/Keras and wire LSTMForecaster, "
            "or choose prophet / arima / xgboost / croston."
        )

    def predict(self, periods: int, **kwargs):
        raise ValueError("LSTM is not enabled in this deployment.")


class CrostonForecaster(BaseForecaster):
    """Croston's method forecaster for intermittent and slow-moving materials"""

    def __init__(self, alpha: float = 0.1):
        super().__init__("croston")
        self.alpha = alpha
        self._last_hist = None
        self._ts = None

    def train(self, df: pd.DataFrame, **kwargs):
        df = df.copy()
        df["ds"] = pd.to_datetime(df["ds"])
        self._ts = df.sort_values("ds")["y"]
        self._last_hist = df["ds"].max()

    def predict(self, periods: int, **kwargs) -> pd.DataFrame:
        from ml_utils.croston import fit_predict_croston
        res = fit_predict_croston(self._ts, forecast_days=periods, alpha=self.alpha)
        start = pd.to_datetime(self._last_hist).normalize() + pd.Timedelta(days=1)
        dates = pd.date_range(start=start, periods=periods, freq="D")
        return pd.DataFrame(
            {"ds": dates, "yhat": res["predictions"], "yhat_lower": res["lower_bound"], "yhat_upper": res["upper_bound"]}
        )


def _select_auto_model(df: pd.DataFrame) -> str:
    n_points = len(df)
    y = df["y"].values
    zero_ratio = float(np.mean(y == 0)) if n_points > 0 else 0.0
    if zero_ratio > 0.30:
        return "croston"
    if n_points < 40:
        return "arima"
    if n_points < 160:
        return "xgboost"
    return "prophet"


class ForecastService:
    """High-level forecast operations"""

    def __init__(self, model_type=None):
        self.model_registry = {
            "prophet": ProphetForecaster,
            "arima": ARIMAForecaster,
            "xgboost": XGBoostForecaster,
            "croston": CrostonForecaster,
            "lstm": LSTMForecaster,
        }
        key = _normalize_model_key(model_type)
        self.model_type = key

    def get_forecaster(self, model_key: str):
        key = _normalize_model_key(model_key)
        if key == "auto":
            key = "prophet"
        cls = self.model_registry.get(key)
        if not cls:
            raise ValueError(f"Unknown model type: {model_key}")
        return cls()

    def train_and_forecast(
        self,
        df: pd.DataFrame,
        horizon_days: int = 365,
        confidence_interval: float = 0.95,
        model_type: Optional[str] = None,
    ) -> Dict:
        import time

        start_time = time.time()
        df = df.copy()
        df["ds"] = pd.to_datetime(df["ds"])
        df["y"] = df["y"].astype(float)

        raw_key = model_type or self.model_type
        nk = _normalize_model_key(raw_key)
        if nk == "auto":
            nk = _select_auto_model(df)
        logger.info("Training %s on %s points (horizon=%s)", nk, len(df), horizon_days)

        last_error: Optional[Exception] = None
        candidates = [nk]
        if nk == "prophet":
            candidates.extend(["xgboost", "arima"])
        elif nk == "xgboost":
            candidates.append("arima")

        forecast_df = None
        for candidate in candidates:
            try:
                forecaster = self.get_forecaster(candidate)
                forecaster.train(df)
                forecast_df = forecaster.predict(periods=horizon_days)
                nk = candidate
                break
            except Exception as exc:
                last_error = exc
                logger.warning("Model %s failed, trying fallback: %s", candidate, exc)

        if forecast_df is None:
            raise ValueError(
                f"All forecast models failed. Last error: {last_error}"
            ) from last_error

        forecast_df["ds"] = pd.to_datetime(forecast_df["ds"])
        last_hist = pd.to_datetime(df["ds"].max()).normalize()
        future_only = forecast_df[forecast_df["ds"] > last_hist].copy()
        if future_only.empty:
            future_only = forecast_df.tail(horizon_days)
        future_only = future_only.head(horizon_days)

        forecast_data = []
        for _, row in future_only.iterrows():
            forecast_data.append(
                {
                    "date": row["ds"].strftime("%Y-%m-%d"),
                    "predicted": round(float(row["yhat"]), 4),
                    "lower_bound": round(float(row.get("yhat_lower", row["yhat"] * 0.9)), 4),
                    "upper_bound": round(float(row.get("yhat_upper", row["yhat"] * 1.1)), 4),
                }
            )

        hist_pred = forecast_df[forecast_df["ds"].isin(df["ds"])].sort_values("ds")
        predicted_vals = hist_pred["yhat"].values
        actual_vals = df.sort_values("ds")["y"].values

        min_len = min(len(predicted_vals), len(actual_vals))
        if min_len > 0:
            metrics = forecaster.evaluate(
                actual_vals[-min_len:], predicted_vals[-min_len:]
            )
        else:
            metrics = {"mae": None, "rmse": None, "mape": None}

        execution_time = time.time() - start_time
        logger.info("%s forecast done in %.2fs", nk, execution_time)

        return {
            "forecast": forecast_data,
            "metrics": metrics,
            "model_type": nk,
            "execution_time_seconds": round(execution_time, 2),
        }


def get_forecast_service() -> ForecastService:
    return ForecastService()
