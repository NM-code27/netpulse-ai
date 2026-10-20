"""
An honest "does the methodology generalize" check, run on genuinely real
RIPE Atlas internet measurement data (see fetch_ripe_atlas.py).

This deliberately does NOT run the enterprise-trained latency_ms model
against this data -- that model's scale (baseline ~25ms, diurnal amplitude
~10ms) was tuned to the synthetic 20-branch-office scenario, and real RTT to
a DNS root server aggregated across thousands of global probes lives on a
different scale entirely, so a direct comparison would be scientifically
misleading either way it came out.

Instead this fits a small fresh model directly on the real series, using
the exact same feature engineering and chronological train/test split
methodology as app/ml/train.py, and reports its held-out MAE against a
naive persistence baseline ("predict next = last observed value"). That's
a fair, scale-appropriate test of whether the *approach* -- not the
specific trained weights -- works on real data.

Run: python -m app.realworld.validate
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
from xgboost import XGBRegressor

from app.ml.features import FEATURE_COLUMNS, compute_features

DATA_DIR = Path(__file__).resolve().parent / "data"
TRAIN_FRACTION = 0.75
HORIZON_STEPS = 3  # 3 x 10-minute buckets = 30 minutes ahead, matching the main pipeline's horizon


def load_series(key: str) -> tuple[pd.DataFrame, dict]:
    with open(DATA_DIR / f"ripe_{key}.json") as f:
        payload = json.load(f)
    df = pd.DataFrame(payload["buckets"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="s", utc=True)
    df = df.rename(columns={"mean_rtt_ms": "value"})[["timestamp", "value"]].sort_values("timestamp")
    return df.reset_index(drop=True), payload["meta"]


def validate_one(key: str) -> dict:
    df, meta = load_series(key)
    if len(df) < 40:
        return {"available": False, "label": meta["label"], "reason": "not enough real data fetched"}

    feat = compute_features(df)
    feat["target_value"] = feat["value"].shift(-HORIZON_STEPS)
    feat = feat.dropna(subset=["target_value"]).reset_index(drop=True)

    split = int(len(feat) * TRAIN_FRACTION)
    train, test = feat.iloc[:split], feat.iloc[split:]
    if len(test) < 5:
        return {"available": False, "label": meta["label"], "reason": "not enough held-out real data"}

    model = XGBRegressor(n_estimators=100, max_depth=3, learning_rate=0.1, random_state=42)
    model.fit(train[FEATURE_COLUMNS], train["target_value"])
    y_pred = model.predict(test[FEATURE_COLUMNS])
    y_true = test["target_value"].to_numpy()

    model_mae = float(np.mean(np.abs(y_true - y_pred)))
    naive_pred = test["value"].to_numpy()  # "predict no change" baseline
    naive_mae = float(np.mean(np.abs(y_true - naive_pred)))

    return {
        "available": True,
        "label": meta["label"],
        "target": meta["target"],
        "n_points": int(len(df)),
        "n_test_points": int(len(test)),
        "real_mean_rtt_ms": round(float(df["value"].mean()), 2),
        "real_std_rtt_ms": round(float(df["value"].std()), 2),
        "model_mae_ms": round(model_mae, 3),
        "naive_persistence_mae_ms": round(naive_mae, 3),
        "model_beats_naive": model_mae < naive_mae,
        "series": [
            {"timestamp": t.isoformat(), "value": v}
            for t, v in zip(df["timestamp"], df["value"])
        ],
    }


def build_report() -> dict:
    sources = []
    for key in ["1001", "1004"]:
        if (DATA_DIR / f"ripe_{key}.json").exists():
            sources.append(validate_one(key))
    return {"sources": sources}


if __name__ == "__main__":
    report = build_report()
    out_path = DATA_DIR / "validation_report.json"
    with open(out_path, "w") as f:
        json.dump(report, f, indent=2)
    for s in report["sources"]:
        if s.get("available"):
            print(f"{s['label']}: model MAE={s['model_mae_ms']}ms vs naive={s['naive_persistence_mae_ms']}ms "
                  f"({'beats' if s['model_beats_naive'] else 'does not beat'} naive baseline)")
        else:
            print(f"{s.get('label')}: unavailable ({s.get('reason')})")
    print(f"\nWritten to {out_path}")
