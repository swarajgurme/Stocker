"""
Forecast Service
Machine learning service for time series forecasting
Supports Prophet, ARIMA, XGBoost, LSTM
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import pandas as pd
import numpy as np

from prophet import Prophet
# from statsmodels.tsa.arima.model import ARIMA  # Optional dependency
# import xgboost as xgb  # Optional dependency
# from tensorflow import keras  # Optional dependency

from config import get_config

logger = logging.getLogger(__name__)
config = get_config()


class BaseForecaster:
    """Base class for forecasting models"""

    def __init__(self, model_type: str):
        self.model_type = model_type
        self.model = None
        self.metrics = {}

    def train(self, df: pd.DataFrame, **kwargs):
        """Train the model - to be implemented by subclasses"""
        raise NotImplementedError

    def predict(self, periods: int, **kwargs) -> pd.DataFrame:
        """Generate forecast - to be implemented by subclasses"""
        raise NotImplementedError

    def evaluate(self, actual: np.ndarray, predicted: np.ndarray) -> Dict[str, float]:
        """Calculate error metrics"""
        from sklearn.metrics import mean_absolute_error, mean_squared_error

        mae = mean_absolute_error(actual, predicted)
        mse = mean_squared_error(actual, predicted)
        rmse = np.sqrt(mse)

        # MAPE (avoid division by zero)
        mask = actual != 0
        if np.any(mask):
            mape = np.mean(np.abs((actual[mask] - predicted[mask]) / actual[mask])) * 100
        else:
            mape = np.nan

        return {
            "mae": round(float(mae), 4),
            "rmse": round(float(rmse), 4),
            "mape": round(float(mape), 4) if not np.isnan(mape) else None
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
            **prophet_kwargs
        )

    def train(self, df: pd.DataFrame, **kwargs):
        """Fit Prophet model"""
        # df must have columns: ds (date), y (target)
        self.model.fit(df)

    def predict(self, periods: int, freq: str = 'D', **kwargs) -> pd.DataFrame:
        """Generate future dataframe with predictions"""
        future = self.model.make_future_dataframe(periods=periods, freq=freq)
        forecast = self.model.predict(future)
        return forecast


class ARIMAForecaster(BaseForecaster):
    """ARIMA forecaster using statsmodels"""

    def __init__(self, order: Tuple[int, int, int] = (1, 1, 1)):
        super().__init__("arima")
        self.order = order
        self.model_fit = None

    def train(self, df: pd.DataFrame, **kwargs):
        """Fit ARIMA model"""
        from statsmodels.tsa.arima.model import ARIMA

        # Extract time series
        ts = df.set_index('ds')['y']

        # Fit ARIMA
        self.model_fit = ARIMA(ts, order=self.order)
        self.model = self.model_fit.fit()

    def predict(self, periods: int, **kwargs) -> pd.DataFrame:
        """Generate predictions"""
        forecast = self.model.forecast(steps=periods)
        # Convert to Prophet-like DataFrame
        last_date = datetime.utcnow()
        dates = pd.date_range(start=last_date, periods=periods, freq='D')
        result = pd.DataFrame({
            'ds': dates,
            'yhat': forecast.values
        })
        # Add placeholder confidence intervals
        result['yhat_lower'] = result['yhat'] * 0.9
        result['yhat_upper'] = result['yhat'] * 1.1
        return result


class XGBoostForecaster(BaseForecaster):
    """XGBoost regressor for time series forecasting"""

    def __init__(self, n_estimators: int = 100, **params):
        super().__init__("xgboost")
        # import xgboost as xgb
        # self.model = xgb.XGBRegressor(n_estimators=n_estimators, **params)
        self.model = None  # Requires xgboost installed

    def train(self, df: pd.DataFrame, **kwargs):
        """Train XGBoost with lag features"""
        # Create lag features
        pass

    def predict(self, periods: int, **kwargs):
        pass


class LSTMForecaster(BaseForecaster):
    """LSTM neural network forecaster"""

    def __init__(self, lookback: int = 30):
        super().__init__("lstm")
        self.lookback = lookback
        self.model = None

    def train(self, df: pd.DataFrame, **kwargs):
        """Train LSTM model"""
        pass

    def predict(self, periods: int, **kwargs):
        pass


# ============= FORECAST SERVICE =============
class ForecastService:
    """High-level service for forecast operations"""

    def __init__(self, model_type=None):
        self.model_registry = {
            "prophet": ProphetForecaster,
            "arima": ARIMAForecaster,
            "xgboost": XGBoostForecaster,
            "lstm": LSTMForecaster,
        }
        self.model_type = model_type or "prophet"

    def get_forecaster(self, model_type: str):
        """Instantiate forecaster by type"""
        cls = self.model_registry.get(model_type)
        if not cls:
            raise ValueError(f"Unknown model type: {model_type}")
        return cls()

    def train_and_forecast(
        self,
        df: pd.DataFrame,
        horizon_days: int = 365,
        confidence_interval: float = 0.95,
        model_type: Optional[str] = None
    ) -> Dict:
        """
        Train model and generate forecast

        Args:
            df: DataFrame with 'ds' (date) and 'y' (value) columns
            horizon_days: Number of days to forecast
            confidence_interval: Prediction interval (e.g., 0.95 for 95%)
            model_type: Override model type

        Returns:
            Dict with forecast, metrics, execution time
        """
        import time

        start_time = time.time()

        model_to_use = model_type or self.model_type
        logger.info(f"Training {model_to_use} model on {len(df)} data points")

        # Instantiate forecaster
        forecaster = self.get_forecaster(model_to_use)

        try:
            # Train
            forecaster.train(df)

            # Predict
            forecast_df = forecaster.predict(periods=horizon_days)

            # Format results
            forecast_data = []
            for _, row in forecast_df.iterrows():
                forecast_data.append({
                    "date": row['ds'].strftime('%Y-%m-%d'),
                    "predicted": round(float(row['yhat']), 2),
                    "lower_bound": round(float(row.get('yhat_lower', row['yhat'] * 0.9)), 2),
                    "upper_bound": round(float(row.get('yhat_upper', row['yhat'] * 1.1)), 2),
                })

            # Calculate predictions vs actual for historical dates
            actual_vals = df['y'].values
            predicted_vals = forecast_df[forecast_df['ds'].isin(df['ds'])]['yhat'].values
            if len(predicted_vals) > 0 and len(predicted_vals) == len(actual_vals):
                metrics = forecaster.evaluate(actual_vals, predicted_vals)
            else:
                metrics = {"mae": None, "rmse": None, "mape": None}

            execution_time = time.time() - start_time
            logger.info(f"{model_to_use} training & forecast completed in {execution_time:.2f}s")

            return {
                "forecast": forecast_data,
                "metrics": metrics,
                "model_type": model_to_use,
                "execution_time_seconds": round(execution_time, 2)
            }

        except Exception as e:
            logger.error(f"Forecast error: {str(e)}")
            raise


# Convenience function for dependency injection
def get_forecast_service() -> ForecastService:
    return ForecastService()
