"""Breach thresholds used for labeling training data, scoring risk, and alerting.
These are the lines that separate "healthy" from "degraded" for each metric family."""

BREACH_THRESHOLDS = {
    "latency_ms": 120.0,
    "packet_loss_pct": 3.0,
    "jitter_ms": 10.0,
    "bandwidth_util_pct": 90.0,
    "cpu_pct": 90.0,
    "resolution_time_ms": 150.0,
    "response_time_ms": 250.0,
    "app_response_time_ms": 220.0,
}

METRIC_NAMES = list(BREACH_THRESHOLDS.keys())
HORIZONS_MINUTES = [10, 20, 30]
