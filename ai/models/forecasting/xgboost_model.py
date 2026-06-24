# =============================================================================
# Jersey Ice Cream Platform — Demand Forecasting (XGBoost)
# =============================================================================
# Primary forecasting model using XGBoost with engineered features.
#
# Model Selection Rationale:
#   XGBoost chosen as primary model because:
#   1. Handles missing data natively (weather API failures, GPS drops)
#   2. Provides feature importance for business explainability
#   3. Fast training (~minutes) enables daily retraining
#   4. Scales linearly with data size
#   5. Battle-tested at Uber, Airbnb, and similar demand forecasting systems
#
# Feature Categories:
#   - Temporal: hour, day_of_week, month, is_holiday, is_weekend
#   - Weather: temperature, humidity, heat_index, precipitation
#   - Spatial: geohash, territory, nearby_schools, nearby_events
#   - Historical: sales_lag_1h, sales_lag_4h, sales_lag_1d, sales_lag_7d
#   - Events: cricket_match, festival, wedding_season
#   - Mood: mood_commerce_score
#   - Competition: competitor_promo_active
#
# DSA:
#   - XGBoost: O(n × d × K × log n) training where n=samples, d=features, K=trees
#   - Feature engineering: O(n) per feature with pre-computed lookups
#   - Prediction: O(K × depth) per sample ≈ O(1) effectively
# =============================================================================

from __future__ import annotations

import logging
import pickle
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)


# ─── Feature Definitions ────────────────────────────────────────────────────

FEATURE_COLUMNS = [
    # Temporal features
    "hour_of_day",
    "day_of_week",
    "day_of_month",
    "month",
    "is_weekend",
    "is_holiday",
    "is_school_vacation",
    "days_since_month_start",
    "quarter",
    # Weather features
    "temperature_celsius",
    "feels_like_celsius",
    "humidity_percent",
    "precipitation_mm",
    "uv_index",
    "is_rain",
    "is_extreme_heat",  # > 42°C
    "heat_index",
    # Historical demand features
    "sales_lag_1h",
    "sales_lag_4h",
    "sales_lag_1d",
    "sales_lag_7d",
    "sales_rolling_mean_24h",
    "sales_rolling_std_24h",
    "sales_same_hour_last_week",
    "sales_ewm_alpha03",
    # Cart/Location features
    "cart_type_encoded",
    "territory_encoded",
    "nearby_cart_count",
    "distance_to_nearest_school_km",
    "population_density",
    # Event features
    "cricket_match_active",
    "ipl_match_local",
    "local_festival_active",
    "wedding_season_score",
    "exam_result_day",
    # Mood commerce score
    "mood_commerce_score",
    # Competition
    "competitor_promo_active",
    "competitor_price_change",
    # Product features
    "product_category_encoded",
    "product_price_tier",
    "is_seasonal_product",
]


# ─── Data Classes ────────────────────────────────────────────────────────────


@dataclass
class ForecastResult:
    """Single forecast prediction."""

    predicted_demand: float
    confidence_lower: float
    confidence_upper: float
    confidence_level: float
    feature_importance: dict[str, float]
    model_version: str
    forecast_horizon: str
    forecast_for: datetime
    generated_at: datetime
    input_features: dict[str, float]


@dataclass
class ModelMetrics:
    """Model evaluation metrics."""

    mape: float  # Mean Absolute Percentage Error
    mae: float  # Mean Absolute Error
    rmse: float  # Root Mean Squared Error
    r2: float  # R-squared
    samples: int
    training_time_seconds: float


# ─── Feature Engineering ─────────────────────────────────────────────────────


class FeatureEngineer:
    """
    Transform raw data into model-ready features.

    Handles:
    - Temporal feature extraction from timestamps
    - Weather feature normalization
    - Historical lag feature computation
    - Event encoding
    - Missing value imputation
    """

    # Indian public holidays (extendable)
    HOLIDAYS_2026 = {
        (1, 26),  # Republic Day
        (3, 14),  # Holi
        (4, 14),  # Ambedkar Jayanti
        (5, 1),   # May Day
        (8, 15),  # Independence Day
        (10, 2),  # Gandhi Jayanti
        (10, 12), # Dussehra
        (11, 1),  # Diwali
        (12, 25), # Christmas
    }

    SCHOOL_VACATION_PERIODS = [
        ((4, 15), (6, 15)),  # Summer vacation
        ((10, 1), (10, 15)),  # Dussehra break
        ((12, 20), (1, 5)),  # Winter break
    ]

    def engineer_temporal_features(self, timestamp: datetime) -> dict[str, float]:
        """Extract temporal features from a timestamp."""
        return {
            "hour_of_day": float(timestamp.hour),
            "day_of_week": float(timestamp.weekday()),
            "day_of_month": float(timestamp.day),
            "month": float(timestamp.month),
            "is_weekend": float(timestamp.weekday() >= 5),
            "is_holiday": float(
                (timestamp.month, timestamp.day) in self.HOLIDAYS_2026
            ),
            "is_school_vacation": float(self._is_school_vacation(timestamp)),
            "days_since_month_start": float(timestamp.day - 1),
            "quarter": float((timestamp.month - 1) // 3 + 1),
        }

    def engineer_weather_features(
        self,
        temperature: float | None,
        humidity: float | None,
        precipitation: float | None,
        uv_index: float | None,
    ) -> dict[str, float]:
        """Engineer weather features with safe defaults for missing data."""
        temp = temperature if temperature is not None else 30.0  # Assume warm
        humid = humidity if humidity is not None else 60.0
        precip = precipitation if precipitation is not None else 0.0
        uv = uv_index if uv_index is not None else 5.0

        # Heat index (simplified Steadman formula)
        heat_idx = temp + 0.5 * (6.1 * (humid / 100.0))

        return {
            "temperature_celsius": temp,
            "feels_like_celsius": heat_idx,
            "humidity_percent": humid,
            "precipitation_mm": precip,
            "uv_index": uv,
            "is_rain": float(precip > 0.5),
            "is_extreme_heat": float(temp > 42.0),
            "heat_index": heat_idx,
        }

    def engineer_historical_features(
        self,
        sales_history: list[float],  # Hourly sales, most recent first
    ) -> dict[str, float]:
        """
        Compute lag and rolling features from sales history.

        Args:
            sales_history: List of hourly sales values, index 0 = most recent hour
        """
        if not sales_history:
            return {
                "sales_lag_1h": 0.0,
                "sales_lag_4h": 0.0,
                "sales_lag_1d": 0.0,
                "sales_lag_7d": 0.0,
                "sales_rolling_mean_24h": 0.0,
                "sales_rolling_std_24h": 0.0,
                "sales_same_hour_last_week": 0.0,
                "sales_ewm_alpha03": 0.0,
            }

        arr = np.array(sales_history, dtype=np.float64)

        # Lag features
        lag_1h = arr[0] if len(arr) > 0 else 0.0
        lag_4h = arr[3] if len(arr) > 3 else lag_1h
        lag_1d = arr[23] if len(arr) > 23 else lag_1h
        lag_7d = arr[167] if len(arr) > 167 else lag_1d

        # Rolling statistics (24-hour window)
        window_24h = arr[:24] if len(arr) >= 24 else arr
        rolling_mean = float(np.mean(window_24h))
        rolling_std = float(np.std(window_24h))

        # Same hour last week
        same_hour_last_week = arr[168] if len(arr) > 168 else lag_1d

        # Exponential weighted mean (alpha=0.3)
        alpha = 0.3
        ewm = float(arr[0])
        for i in range(1, min(len(arr), 24)):
            ewm = alpha * arr[i] + (1 - alpha) * ewm

        return {
            "sales_lag_1h": float(lag_1h),
            "sales_lag_4h": float(lag_4h),
            "sales_lag_1d": float(lag_1d),
            "sales_lag_7d": float(lag_7d),
            "sales_rolling_mean_24h": rolling_mean,
            "sales_rolling_std_24h": rolling_std,
            "sales_same_hour_last_week": float(same_hour_last_week),
            "sales_ewm_alpha03": ewm,
        }

    def _is_school_vacation(self, dt: datetime) -> bool:
        """Check if date falls in school vacation period."""
        for (start_m, start_d), (end_m, end_d) in self.SCHOOL_VACATION_PERIODS:
            if start_m <= dt.month <= end_m:
                if start_m == dt.month and dt.day < start_d:
                    continue
                if end_m == dt.month and dt.day > end_d:
                    continue
                return True
        return False


# ─── XGBoost Forecasting Model ──────────────────────────────────────────────


class DemandForecaster:
    """
    XGBoost-based demand forecasting model.

    Supports:
    - Training with feature-engineered data
    - Prediction with confidence intervals
    - Feature importance extraction
    - Model persistence (save/load)
    - Quantile regression for confidence bounds
    """

    def __init__(self, model_version: str = "0.1.0") -> None:
        self.model = None
        self.model_lower = None  # For lower confidence bound
        self.model_upper = None  # For upper confidence bound
        self.model_version = model_version
        self.feature_engineer = FeatureEngineer()
        self._trained = False

    def train(
        self,
        X: np.ndarray,
        y: np.ndarray,
        feature_names: list[str] | None = None,
    ) -> ModelMetrics:
        """
        Train the XGBoost model.

        Uses 3-fold time-series cross-validation with expanding window.

        Args:
            X: Feature matrix (n_samples, n_features)
            y: Target vector (n_samples,)
            feature_names: Feature names for importance tracking

        Returns:
            ModelMetrics with evaluation results
        """
        import time as time_module

        start = time_module.monotonic()

        try:
            import xgboost as xgb
            from sklearn.model_selection import TimeSeriesSplit

            # Main model (point estimate)
            self.model = xgb.XGBRegressor(
                n_estimators=500,
                max_depth=8,
                learning_rate=0.05,
                subsample=0.8,
                colsample_bytree=0.8,
                min_child_weight=5,
                gamma=0.1,
                reg_alpha=0.1,
                reg_lambda=1.0,
                objective="reg:squarederror",
                tree_method="hist",  # Fast histogram-based method
                n_jobs=-1,
                random_state=42,
                early_stopping_rounds=50,
            )

            # Time-series split for validation
            tscv = TimeSeriesSplit(n_splits=3)
            maes, mapes = [], []

            for train_idx, val_idx in tscv.split(X):
                X_train, X_val = X[train_idx], X[val_idx]
                y_train, y_val = y[train_idx], y[val_idx]

                self.model.fit(
                    X_train,
                    y_train,
                    eval_set=[(X_val, y_val)],
                    verbose=False,
                )

                y_pred = self.model.predict(X_val)
                mae = float(np.mean(np.abs(y_pred - y_val)))
                # MAPE with protection against zero division
                mask = y_val > 0
                mape = float(np.mean(np.abs((y_val[mask] - y_pred[mask]) / y_val[mask])) * 100) if mask.any() else 0.0

                maes.append(mae)
                mapes.append(mape)

            # Final train on all data
            self.model.fit(X, y, verbose=False)

            # Train quantile models for confidence intervals
            self.model_lower = xgb.XGBRegressor(
                n_estimators=200,
                max_depth=6,
                learning_rate=0.05,
                objective="reg:quantileerror",
                quantile_alpha=0.025,
                tree_method="hist",
                n_jobs=-1,
                random_state=42,
            )
            self.model_lower.fit(X, y, verbose=False)

            self.model_upper = xgb.XGBRegressor(
                n_estimators=200,
                max_depth=6,
                learning_rate=0.05,
                objective="reg:quantileerror",
                quantile_alpha=0.975,
                tree_method="hist",
                n_jobs=-1,
                random_state=42,
            )
            self.model_upper.fit(X, y, verbose=False)

            self._trained = True
            training_time = time_module.monotonic() - start

            # Final metrics
            y_pred_final = self.model.predict(X)
            rmse = float(np.sqrt(np.mean((y_pred_final - y) ** 2)))
            ss_res = np.sum((y - y_pred_final) ** 2)
            ss_tot = np.sum((y - np.mean(y)) ** 2)
            r2 = float(1 - ss_res / ss_tot) if ss_tot > 0 else 0.0

            metrics = ModelMetrics(
                mape=float(np.mean(mapes)),
                mae=float(np.mean(maes)),
                rmse=rmse,
                r2=r2,
                samples=len(y),
                training_time_seconds=round(training_time, 2),
            )

            logger.info(
                "Model trained: MAPE=%.2f%% MAE=%.2f R²=%.3f time=%.1fs",
                metrics.mape,
                metrics.mae,
                metrics.r2,
                metrics.training_time_seconds,
            )

            return metrics

        except ImportError:
            logger.warning("xgboost not installed — using mock model")
            self._trained = False
            return ModelMetrics(
                mape=0.0, mae=0.0, rmse=0.0, r2=0.0,
                samples=0, training_time_seconds=0.0,
            )

    def predict(
        self,
        features: dict[str, float],
        horizon: str = "1h",
    ) -> ForecastResult:
        """
        Generate a demand forecast with confidence interval.

        Args:
            features: Feature dictionary (all FEATURE_COLUMNS must be present)
            horizon: Forecast horizon ('1h', '4h', 'daily', 'weekly')

        Returns:
            ForecastResult with prediction and confidence bounds
        """
        now = datetime.now(UTC)

        # Build feature vector
        feature_vector = np.array(
            [features.get(col, 0.0) for col in FEATURE_COLUMNS]
        ).reshape(1, -1)

        if self._trained and self.model is not None:
            predicted = float(self.model.predict(feature_vector)[0])
            lower = float(self.model_lower.predict(feature_vector)[0])
            upper = float(self.model_upper.predict(feature_vector)[0])

            # Get feature importance
            importance = {}
            if hasattr(self.model, "feature_importances_"):
                for i, col in enumerate(FEATURE_COLUMNS):
                    if i < len(self.model.feature_importances_):
                        importance[col] = round(float(self.model.feature_importances_[i]), 4)
        else:
            # Mock prediction for development
            base = features.get("sales_lag_1h", 5.0)
            temp_factor = max(0.5, min(2.0, features.get("temperature_celsius", 30.0) / 30.0))
            mood_factor = 1.0 + features.get("mood_commerce_score", 0.0) * 0.5

            predicted = max(0, base * temp_factor * mood_factor)
            lower = max(0, predicted * 0.7)
            upper = predicted * 1.3
            importance = {"temperature_celsius": 0.25, "sales_lag_1h": 0.20, "hour_of_day": 0.15}

        # Ensure non-negative
        predicted = max(0, predicted)
        lower = max(0, lower)

        # Calculate forecast_for timestamp based on horizon
        from datetime import timedelta

        horizon_map = {
            "1h": timedelta(hours=1),
            "4h": timedelta(hours=4),
            "daily": timedelta(days=1),
            "weekly": timedelta(weeks=1),
        }
        forecast_for = now + horizon_map.get(horizon, timedelta(hours=1))

        return ForecastResult(
            predicted_demand=round(predicted, 2),
            confidence_lower=round(lower, 2),
            confidence_upper=round(upper, 2),
            confidence_level=0.95,
            feature_importance=importance,
            model_version=self.model_version,
            forecast_horizon=horizon,
            forecast_for=forecast_for,
            generated_at=now,
            input_features={k: round(v, 4) for k, v in features.items()},
        )

    def save_model(self, directory: str) -> None:
        """Save model weights to disk."""
        path = Path(directory)
        path.mkdir(parents=True, exist_ok=True)

        if self.model is not None:
            with open(path / "model_main.pkl", "wb") as f:
                pickle.dump(self.model, f)
            with open(path / "model_lower.pkl", "wb") as f:
                pickle.dump(self.model_lower, f)
            with open(path / "model_upper.pkl", "wb") as f:
                pickle.dump(self.model_upper, f)

            logger.info("Models saved to %s", directory)

    def load_model(self, directory: str) -> bool:
        """Load model weights from disk."""
        path = Path(directory)
        main_path = path / "model_main.pkl"

        if not main_path.exists():
            logger.warning("Model not found at %s", directory)
            return False

        try:
            with open(path / "model_main.pkl", "rb") as f:
                self.model = pickle.load(f)  # noqa: S301
            with open(path / "model_lower.pkl", "rb") as f:
                self.model_lower = pickle.load(f)  # noqa: S301
            with open(path / "model_upper.pkl", "rb") as f:
                self.model_upper = pickle.load(f)  # noqa: S301

            self._trained = True
            logger.info("Models loaded from %s", directory)
            return True
        except Exception:
            logger.error("Failed to load models", exc_info=True)
            return False


# ─── Singleton ───────────────────────────────────────────────────────────────

_forecaster: DemandForecaster | None = None


def get_demand_forecaster() -> DemandForecaster:
    """Get or create the singleton demand forecaster."""
    global _forecaster
    if _forecaster is None:
        _forecaster = DemandForecaster()
        from app.config import get_settings

        settings = get_settings()
        _forecaster.load_model(settings.forecast_model_path)
    return _forecaster
