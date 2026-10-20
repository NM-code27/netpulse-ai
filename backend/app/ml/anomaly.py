"""
Per-metric-family anomaly detection (Isolation Forest), trained only on
non-fault ("normal") historical windows so the model learns the healthy
envelope -- including its diurnal swing -- rather than being contaminated
by the very incidents it's supposed to flag.
"""
from pathlib import Path

import joblib
import pandas as pd
from sklearn.ensemble import IsolationForest

from app.ml.features import FEATURE_COLUMNS

ARTIFACT_DIR = Path(__file__).resolve().parent / "artifacts"
_MODEL_CACHE: dict[str, object] = {}


def _path(metric_name: str) -> Path:
    return ARTIFACT_DIR / f"anomaly_{metric_name}.joblib"


def train_anomaly_detector(normal_df: pd.DataFrame) -> dict:
    model = IsolationForest(n_estimators=200, contamination=0.02, random_state=42)
    X = normal_df[FEATURE_COLUMNS]
    model.fit(X)
    scores = model.score_samples(X)
    return {"model": model, "score_min": float(scores.min()), "score_max": float(scores.max())}


def save_anomaly_detector(bundle: dict, metric_name: str):
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(bundle, _path(metric_name))


def load_anomaly_detector(metric_name: str) -> dict | None:
    path = _path(metric_name)
    key = str(path)
    if key not in _MODEL_CACHE:
        _MODEL_CACHE[key] = joblib.load(path) if path.exists() else None
    return _MODEL_CACHE[key]


def anomaly_score(metric_name: str, feature_row: pd.Series) -> float | None:
    """0-100, higher = more anomalous relative to this metric's learned normal envelope."""
    bundle = load_anomaly_detector(metric_name)
    if bundle is None:
        return None
    X = feature_row[FEATURE_COLUMNS].to_frame().T
    raw = bundle["model"].score_samples(X)[0]
    lo, hi = bundle["score_min"], bundle["score_max"]
    if hi - lo < 1e-9:
        return 0.0
    normalized = (hi - raw) / (hi - lo)
    return float(max(0.0, min(1.0, normalized)) * 100.0)
