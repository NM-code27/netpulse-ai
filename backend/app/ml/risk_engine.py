"""Combines the forecast-breach classifiers and the anomaly detector into one
outage-risk score (0-100) and a lead-time estimate, for a single metric
family at a single point in time (one feature row)."""
import pandas as pd

from app.ml.anomaly import anomaly_score
from app.ml.forecasting import predict_breach_probabilities
from app.ml.thresholds import HORIZONS_MINUTES


def compute_risk(metric_name: str, feature_row: pd.Series) -> dict:
    anomaly = anomaly_score(metric_name, feature_row) or 0.0
    probs = predict_breach_probabilities(metric_name, feature_row)

    lead_time = None
    for h in HORIZONS_MINUTES:
        if probs.get(h, 0.0) >= 0.5:
            lead_time = h
            break

    max_prob = max(probs.values()) if probs else 0.0
    risk_score = round(100.0 * max(max_prob, (anomaly / 100.0) * 0.6), 1)

    return {
        "anomaly_score": round(anomaly, 1),
        "breach_probabilities": {str(k): round(v, 3) for k, v in probs.items()},
        "lead_time_minutes": lead_time,
        "risk_score": risk_score,
    }
