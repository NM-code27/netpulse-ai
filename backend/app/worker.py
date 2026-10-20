"""
Two background jobs, scheduled from app/main.py on startup:
  - run_tick():    advances the live simulator by one tick (cheap, frequent)
  - run_scoring(): pulls recent history, scores risk/anomaly per site,
                   runs root-cause + business-impact, and opens Alert rows
                   (heavier, less frequent)
Hard device failures (status==0) are detected directly rather than through
the ML models, since "is it up" doesn't need a forecast.
"""
from datetime import datetime, timedelta, timezone

import pandas as pd
from sqlalchemy.orm import Session

from app.db.models import Alert, Entity, Metric
from app.db.session import SessionLocal
from app.ml.anomaly import anomaly_score
from app.ml.business_impact import estimate_impact
from app.ml.features import compute_features, last_feature_row
from app.ml.risk_engine import compute_risk
from app.ml.root_cause import analyze_root_cause
from app.ml.thresholds import METRIC_NAMES
from app.simulator.generator import SimulatorEngine

RISK_ALERT_THRESHOLD = 55.0
ANOMALY_ALERT_THRESHOLD = 60.0
ALERT_COOLDOWN_MINUTES = 5
HISTORY_WINDOW_POINTS = 20

_engine = SimulatorEngine()


def _recent_series(db: Session, entity_id: str, metric_name: str, limit: int = HISTORY_WINDOW_POINTS):
    rows = (db.query(Metric)
            .filter(Metric.entity_id == entity_id, Metric.metric_name == metric_name)
            .order_by(Metric.timestamp.desc()).limit(limit).all())
    rows = list(reversed(rows))
    if not rows:
        return None
    df = pd.DataFrame({"timestamp": [r.timestamp for r in rows], "value": [r.value for r in rows]})
    return compute_features(df)


def build_live_snapshot(db: Session) -> dict:
    entities = db.query(Entity).all()
    snapshot: dict = {}
    for e in entities:
        for metric_name in METRIC_NAMES:
            feat = _recent_series(db, e.id, metric_name)
            if feat is None or feat.empty:
                continue
            score = anomaly_score(metric_name, last_feature_row(feat))
            if score is not None:
                snapshot.setdefault(e.id, {})[metric_name] = score
    return snapshot


def _recent_alert_exists(db: Session, entity_id: str, metric_name: str) -> bool:
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=ALERT_COOLDOWN_MINUTES)
    return db.query(Alert).filter(
        Alert.entity_id == entity_id, Alert.metric_name == metric_name, Alert.created_at >= cutoff,
    ).first() is not None


def score_and_alert(db: Session):
    entities = {e.id: e for e in db.query(Entity).all()}
    sites = [e for e in entities.values() if e.type == "site"]
    snapshot: dict | None = None

    for site in sites:
        feat = _recent_series(db, site.id, "app_response_time_ms")
        if feat is None or len(feat) < 3:
            continue
        risk = compute_risk("app_response_time_ms", last_feature_row(feat))

        if risk["risk_score"] < RISK_ALERT_THRESHOLD and risk["anomaly_score"] < ANOMALY_ALERT_THRESHOLD:
            continue
        if _recent_alert_exists(db, site.id, "app_response_time_ms"):
            continue

        if snapshot is None:
            snapshot = build_live_snapshot(db)

        root_cause = analyze_root_cause(site.id, snapshot)
        impact = estimate_impact(root_cause[0]["category"], site.id, snapshot)

        alert_type = "predictive_risk" if risk["lead_time_minutes"] is not None else "anomaly"
        severity = "critical" if risk["risk_score"] >= 80 else "warning"
        lead = risk["lead_time_minutes"]
        message = (
            f"{site.name}: application response time trending toward breach (risk {risk['risk_score']}/100"
            + (f", ~{lead} min warning" if lead is not None else "") + f"). Likely cause: {root_cause[0]['label']}."
        )

        db.add(Alert(
            entity_id=site.id, alert_type=alert_type, severity=severity,
            metric_name="app_response_time_ms", risk_score=risk["risk_score"],
            lead_time_minutes=lead, message=message,
            root_cause={"candidates": root_cause, "anomaly_score": risk["anomaly_score"],
                        "breach_probabilities": risk["breach_probabilities"]},
            business_impact=impact,
        ))

    for e in entities.values():
        if e.type not in ("router", "switch"):
            continue
        feat = _recent_series(db, e.id, "status")
        if feat is None or feat.empty or feat.iloc[-1]["value"] != 0.0:
            continue
        if _recent_alert_exists(db, e.id, "status"):
            continue
        site = entities.get(e.parent_id)
        impact = estimate_impact("device", site.id if site else e.id, snapshot or {})
        db.add(Alert(
            entity_id=e.id, alert_type="anomaly", severity="critical",
            metric_name="status", risk_score=100.0, lead_time_minutes=0.0,
            message=f"{e.name} at {site.name if site else e.parent_id} is DOWN.",
            root_cause={"candidates": [{"category": "device", "entity_id": e.id,
                                         "label": "Device down", "confidence": 100.0}]},
            business_impact=impact,
        ))

    db.commit()


def run_tick():
    db = SessionLocal()
    try:
        _engine.tick(db)
    finally:
        db.close()


def run_scoring():
    db = SessionLocal()
    try:
        score_and_alert(db)
    finally:
        db.close()
