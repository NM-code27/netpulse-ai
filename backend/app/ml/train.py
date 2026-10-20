"""
Trains every model NetPulse AI uses, against the historical synthetic
dataset (app/simulator/historical.py), using a strict chronological
train/test split per entity so no future information leaks into the
training set. Writes a training_report.json consumed by the frontend's
Model Evaluation page -- MAE/RMSE for forecasting, precision/recall/PR-AUC
per lead-time horizon for the risk classifiers, an estimated false-alarm
rate, and top-1/top-3 root-cause accuracy against the known fault labels.

Run: python -m app.ml.train
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, mean_absolute_error, mean_squared_error, precision_score, recall_score

from app.data.topology_seed import TOPOLOGY
from app.ml.anomaly import anomaly_score as get_anomaly_score
from app.ml.anomaly import save_anomaly_detector, train_anomaly_detector
from app.ml.features import FEATURE_COLUMNS, compute_features, last_feature_row
from app.ml.forecasting import save_forecaster, save_risk_classifier, train_forecaster, train_risk_classifier
from app.ml.root_cause import analyze_root_cause, category_for_fault_type
from app.ml.thresholds import BREACH_THRESHOLDS, HORIZONS_MINUTES, METRIC_NAMES
from app.simulator.historical import DATA_DIR, generate_historical

RESOLUTION_MINUTES = 2.0
PRIMARY_HORIZON_MINUTES = 30
TRAIN_FRACTION = 0.75
ARTIFACT_DIR = Path(__file__).resolve().parent / "artifacts"

ENTITY_PARENT = {e["id"]: e.get("parent_id") for e in TOPOLOGY["entities"]}
SITE_IDS = [e["id"] for e in TOPOLOGY["entities"] if e["type"] == "site"]


def load_data():
    metrics_path = DATA_DIR / "historical_metrics.parquet"
    faults_path = DATA_DIR / "historical_faults.json"
    if not metrics_path.exists() or not faults_path.exists():
        print("No historical data found -- generating it first (this takes a minute)...")
        generate_historical()
    df = pd.read_parquet(metrics_path)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    with open(faults_path) as f:
        faults = json.load(f)
    return df, faults


def mark_fault_windows(g: pd.DataFrame, entity_id: str, faults: list) -> pd.Series:
    intervals = [(pd.Timestamp(f["start_time"]), pd.Timestamp(f["end_time"]))
                 for f in faults if f["entity_id"] == entity_id]
    flags = pd.Series(False, index=g.index)
    for start, end in intervals:
        flags |= (g["timestamp"] >= start) & (g["timestamp"] <= end)
    return flags


def forward_breach_label(values: pd.Series, steps: int, threshold: float) -> pd.Series:
    """1 if the metric exceeds `threshold` at any point in the next `steps` ticks (strictly future)."""
    future = values.shift(-1)
    reversed_roll = future[::-1].rolling(window=steps, min_periods=1).max()[::-1].reset_index(drop=True)
    return (reversed_roll > threshold).astype(int)


def build_feature_frame(g: pd.DataFrame, entity_id: str, faults: list, threshold: float,
                         horizon_steps_by_h: dict, primary_steps: int) -> pd.DataFrame:
    g = g.sort_values("timestamp").reset_index(drop=True)
    feat = compute_features(g[["timestamp", "value"]])
    feat["target_value"] = feat["value"].shift(-primary_steps)
    for h, steps in horizon_steps_by_h.items():
        feat[f"target_breach_{h}m"] = forward_breach_label(feat["value"], steps, threshold)
    feat["in_fault"] = mark_fault_windows(g, entity_id, faults).values
    return feat.dropna(subset=["target_value"]).reset_index(drop=True)


def build_snapshot_at(df: pd.DataFrame, target_time: pd.Timestamp, tolerance_minutes: float = 3.0) -> dict:
    """Reconstruct {entity_id: {metric_name: anomaly_score}} for every entity near target_time."""
    window_start = target_time - pd.Timedelta(minutes=40)
    window_end = target_time + pd.Timedelta(minutes=tolerance_minutes)
    sub = df[(df["timestamp"] >= window_start) & (df["timestamp"] <= window_end)]
    snapshot: dict = {}
    for (entity_id, metric_name), g in sub.groupby(["entity_id", "metric_name"]):
        if metric_name not in METRIC_NAMES:
            continue
        g = g.sort_values("timestamp")
        if g.empty:
            continue
        feat = compute_features(g[["timestamp", "value"]])
        score = get_anomaly_score(metric_name, last_feature_row(feat))
        if score is None:
            continue
        snapshot.setdefault(entity_id, {})[metric_name] = score
    return snapshot


def pick_site_for_fault(entity_type: str, entity_id: str, snapshot: dict) -> str | None:
    if entity_type in ("wan_link", "router", "switch"):
        return ENTITY_PARENT.get(entity_id)
    best_site, best_score = None, -1.0
    for s in SITE_IDS:
        score = snapshot.get(s, {}).get("app_response_time_ms", 0.0)
        if score > best_score:
            best_score, best_site = score, s
    return best_site


def evaluate_root_cause(df: pd.DataFrame, faults: list) -> dict:
    """
    Only scores faults whose peak falls in the held-out test period (the
    final (1 - TRAIN_FRACTION) share of the timeline, matching the same
    chronological split used for the forecasting/risk models) -- otherwise
    this metric would be measured against faults the anomaly detectors were
    effectively tuned around, which would overstate accuracy.
    """
    series_start, series_end = df["timestamp"].min(), df["timestamp"].max()
    cutoff_time = series_start + (series_end - series_start) * TRAIN_FRACTION

    top1_hits, top3_hits, total = 0, 0, 0
    examples = []
    for f in faults:
        entity_type = f["entity_type"]
        if entity_type not in ("wan_link", "router", "switch", "dns_resolver", "app_server"):
            continue
        true_category = category_for_fault_type(f["fault_type"])
        start, end = pd.Timestamp(f["start_time"]), pd.Timestamp(f["end_time"])
        peak_time = start + (end - start) * 0.8
        if peak_time < cutoff_time:
            continue

        snapshot = build_snapshot_at(df, peak_time)
        if not snapshot:
            continue
        site_id = pick_site_for_fault(entity_type, f["entity_id"], snapshot)
        if site_id is None:
            continue

        candidates = analyze_root_cause(site_id, snapshot)
        ranking = [c["category"] for c in candidates]
        total += 1
        if ranking and ranking[0] == true_category:
            top1_hits += 1
        if true_category in ranking[:3]:
            top3_hits += 1
        examples.append({
            "fault_type": f["fault_type"], "entity_id": f["entity_id"],
            "true_category": true_category, "predicted_ranking": ranking,
        })

    return {
        "evaluated_on": "held_out_test_period_only",
        "total_faults_evaluated": total,
        "top1_accuracy": round(top1_hits / total, 3) if total else None,
        "top3_accuracy": round(top3_hits / total, 3) if total else None,
        "examples": examples[:12],
    }


def main():
    df, faults = load_data()
    horizon_steps_by_h = {h: max(1, round(h / RESOLUTION_MINUTES)) for h in HORIZONS_MINUTES}
    primary_steps = max(1, round(PRIMARY_HORIZON_MINUTES / RESOLUTION_MINUTES))

    report = {"generated_at": pd.Timestamp.utcnow().isoformat(), "metrics": {}}

    for metric_name in METRIC_NAMES:
        threshold = BREACH_THRESHOLDS[metric_name]
        sub = df[df["metric_name"] == metric_name]
        if sub.empty:
            print(f"[{metric_name}] no data, skipping")
            continue

        train_parts, test_parts, normal_parts = [], [], []
        for entity_id, g in sub.groupby("entity_id"):
            feat = build_feature_frame(g, entity_id, faults, threshold, horizon_steps_by_h, primary_steps)
            if len(feat) < 20:
                continue
            split = int(len(feat) * TRAIN_FRACTION)
            train_parts.append(feat.iloc[:split])
            test_parts.append(feat.iloc[split:])
            normal_parts.append(feat.iloc[:split][~feat.iloc[:split]["in_fault"]])

        if not train_parts:
            continue
        train_df = pd.concat(train_parts, ignore_index=True)
        test_df = pd.concat(test_parts, ignore_index=True)
        normal_df = pd.concat(normal_parts, ignore_index=True)
        if len(train_df) < 50 or len(normal_df) < 50:
            print(f"[{metric_name}] not enough rows ({len(train_df)}), skipping")
            continue

        forecaster = train_forecaster(train_df)
        save_forecaster(forecaster, metric_name)
        y_pred = forecaster.predict(test_df[FEATURE_COLUMNS])
        mae = mean_absolute_error(test_df["target_value"], y_pred)
        rmse = float(np.sqrt(mean_squared_error(test_df["target_value"], y_pred)))

        horizon_metrics = {}
        for h in HORIZONS_MINUTES:
            col = f"target_breach_{h}m"
            clf = train_risk_classifier(train_df, h)
            if clf is None:
                continue
            save_risk_classifier(clf, metric_name, h)
            y_true = test_df[col]
            if y_true.nunique() < 2:
                continue
            y_prob = clf.predict_proba(test_df[FEATURE_COLUMNS])[:, 1]
            y_hat = (y_prob >= 0.5).astype(int)
            horizon_metrics[h] = {
                "precision": round(float(precision_score(y_true, y_hat, zero_division=0)), 3),
                "recall": round(float(recall_score(y_true, y_hat, zero_division=0)), 3),
                "pr_auc": round(float(average_precision_score(y_true, y_prob)), 3),
                "positive_rate_test": round(float(y_true.mean()), 4),
            }

        anomaly_bundle = train_anomaly_detector(normal_df)
        save_anomaly_detector(anomaly_bundle, metric_name)

        normal_test = test_df[~test_df["in_fault"]]
        false_alarm_rate = None
        if len(normal_test) > 0:
            raw = anomaly_bundle["model"].score_samples(normal_test[FEATURE_COLUMNS])
            lo, hi = anomaly_bundle["score_min"], anomaly_bundle["score_max"]
            norm = np.clip((hi - raw) / max(1e-9, hi - lo), 0, 1) * 100
            false_alarms = int((norm > 60).sum())
            span_days = max(1e-6, (test_df["timestamp"].max() - test_df["timestamp"].min()).total_seconds() / 86400)
            n_entities = sub["entity_id"].nunique()
            false_alarm_rate = round(false_alarms / max(1e-6, n_entities * span_days), 3)

        report["metrics"][metric_name] = {
            "forecast": {"mae": round(float(mae), 3), "rmse": round(rmse, 3), "horizon_minutes": PRIMARY_HORIZON_MINUTES},
            "risk_classifiers": horizon_metrics,
            "false_alarms_per_entity_day": false_alarm_rate,
            "train_rows": int(len(train_df)), "test_rows": int(len(test_df)),
        }
        print(f"[{metric_name}] MAE={mae:.2f} RMSE={rmse:.2f} horizons_trained={list(horizon_metrics.keys())} "
              f"false_alarms/entity-day={false_alarm_rate}")

    print("\nEvaluating root-cause correlation against known fault labels...")
    report["root_cause"] = evaluate_root_cause(df, faults)
    print(f"Root cause top-1={report['root_cause']['top1_accuracy']} top-3={report['root_cause']['top3_accuracy']} "
          f"(n={report['root_cause']['total_faults_evaluated']})")

    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = ARTIFACT_DIR / "training_report.json"
    with open(out_path, "w") as f:
        json.dump(report, f, indent=2, default=str)
    print(f"\nTraining report written to {out_path}")


if __name__ == "__main__":
    main()
