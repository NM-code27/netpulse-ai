"""
Per-metric-family forecasting + outage-risk classification.

One regressor and one classifier set per metric_name (8 families: latency_ms,
packet_loss_pct, jitter_ms, bandwidth_util_pct, cpu_pct, resolution_time_ms,
response_time_ms, app_response_time_ms) rather than one model per entity --
entities sharing a metric_name share scale and dynamics, and pooling them
gives each model far more training examples than any single link/device
alone would produce.
"""
from pathlib import Path

import joblib
import pandas as pd
from xgboost import XGBRegressor, XGBClassifier

from app.ml.features import FEATURE_COLUMNS
from app.ml.thresholds import HORIZONS_MINUTES

ARTIFACT_DIR = Path(__file__).resolve().parent / "artifacts"
_MODEL_CACHE: dict[str, object] = {}


def _forecast_path(metric_name: str) -> Path:
    return ARTIFACT_DIR / f"forecast_{metric_name}.joblib"


def _risk_path(metric_name: str, horizon: int) -> Path:
    return ARTIFACT_DIR / f"risk_{metric_name}_{horizon}m.joblib"


def train_forecaster(train_df: pd.DataFrame) -> XGBRegressor:
    model = XGBRegressor(n_estimators=150, max_depth=4, learning_rate=0.08,
                          subsample=0.8, colsample_bytree=0.8, random_state=42)
    model.fit(train_df[FEATURE_COLUMNS], train_df["target_value"])
    return model


def train_risk_classifier(train_df: pd.DataFrame, horizon: int) -> XGBClassifier | None:
    y = train_df[f"target_breach_{horizon}m"]
    if y.nunique() < 2:
        return None
    pos_weight = max(1.0, (y == 0).sum() / max(1, (y == 1).sum()))
    model = XGBClassifier(n_estimators=150, max_depth=4, learning_rate=0.08,
                           subsample=0.8, colsample_bytree=0.8, random_state=42,
                           scale_pos_weight=pos_weight, eval_metric="logloss")
    model.fit(train_df[FEATURE_COLUMNS], y)
    return model


def save_forecaster(model: XGBRegressor, metric_name: str):
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, _forecast_path(metric_name))


def save_risk_classifier(model: XGBClassifier, metric_name: str, horizon: int):
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, _risk_path(metric_name, horizon))


def _cached_load(path: Path):
    key = str(path)
    if key not in _MODEL_CACHE:
        _MODEL_CACHE[key] = joblib.load(path) if path.exists() else None
    return _MODEL_CACHE[key]


def load_forecaster(metric_name: str):
    return _cached_load(_forecast_path(metric_name))


def load_risk_classifier(metric_name: str, horizon: int):
    return _cached_load(_risk_path(metric_name, horizon))


def predict_forecast(metric_name: str, feature_row: pd.Series) -> float | None:
    model = load_forecaster(metric_name)
    if model is None:
        return None
    X = feature_row[FEATURE_COLUMNS].to_frame().T
    return float(model.predict(X)[0])


def predict_breach_probabilities(metric_name: str, feature_row: pd.Series) -> dict:
    """Returns {horizon_minutes: probability_of_breach} for each trained horizon."""
    X = feature_row[FEATURE_COLUMNS].to_frame().T
    probs = {}
    for horizon in HORIZONS_MINUTES:
        model = load_risk_classifier(metric_name, horizon)
        if model is None:
            continue
        probs[horizon] = float(model.predict_proba(X)[0][1])
    return probs
