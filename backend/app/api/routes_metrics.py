from datetime import datetime, timedelta, timezone

import pandas as pd
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.models import Entity, Metric
from app.db.session import get_db
from app.ml.features import compute_features, last_feature_row
from app.ml.risk_engine import compute_risk
from app.schemas import MetricSeriesOut
from app.worker import HISTORY_WINDOW_POINTS

router = APIRouter(prefix="/api/metrics", tags=["metrics"])


@router.get("/overview")
def overview(db: Session = Depends(get_db)):
    sites = db.query(Entity).filter(Entity.type == "site").all()
    out = []
    for site in sites:
        rows = (db.query(Metric)
                .filter(Metric.entity_id == site.id, Metric.metric_name == "app_response_time_ms")
                .order_by(Metric.timestamp.desc()).limit(HISTORY_WINDOW_POINTS).all())
        rows = list(reversed(rows))
        entry = {
            "id": site.id, "name": site.name, "region": site.region, "tier": site.tier,
            "users": (site.extra or {}).get("users"), "apps": (site.extra or {}).get("apps"),
            "latest_value": None, "risk_score": None, "anomaly_score": None, "lead_time_minutes": None,
            "status": "no_data",
        }
        if rows:
            df = pd.DataFrame({"timestamp": [r.timestamp for r in rows], "value": [r.value for r in rows]})
            feat = compute_features(df)
            entry["latest_value"] = round(float(feat.iloc[-1]["value"]), 2)
            if len(rows) >= 3:
                risk = compute_risk("app_response_time_ms", last_feature_row(feat))
                entry["risk_score"] = risk["risk_score"]
                entry["anomaly_score"] = risk["anomaly_score"]
                entry["lead_time_minutes"] = risk["lead_time_minutes"]
                entry["status"] = (
                    "critical" if risk["risk_score"] >= 80 else
                    "warning" if risk["risk_score"] >= 55 or risk["anomaly_score"] >= 60 else
                    "healthy"
                )
            else:
                entry["status"] = "healthy"
        out.append(entry)
    return out


@router.get("/{entity_id}/{metric_name}", response_model=MetricSeriesOut)
def get_series(entity_id: str, metric_name: str, minutes: int = 60, db: Session = Depends(get_db)):
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=minutes)
    rows = (db.query(Metric)
            .filter(Metric.entity_id == entity_id, Metric.metric_name == metric_name, Metric.timestamp >= cutoff)
            .order_by(Metric.timestamp.asc()).all())
    return MetricSeriesOut(
        entity_id=entity_id, metric_name=metric_name,
        points=[{"timestamp": r.timestamp, "value": r.value} for r in rows],
    )


@router.get("/site/{site_id}/detail")
def site_detail(site_id: str, minutes: int = 60, db: Session = Depends(get_db)):
    """All metrics for a site and its direct WAN link/router/switch, for the detail panel."""
    site = db.query(Entity).filter(Entity.id == site_id).first()
    if not site:
        return {"error": "not_found"}
    children = db.query(Entity).filter(Entity.parent_id == site_id).all()
    entity_ids = [site_id] + [c.id for c in children]
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=minutes)
    rows = (db.query(Metric)
            .filter(Metric.entity_id.in_(entity_ids), Metric.timestamp >= cutoff)
            .order_by(Metric.timestamp.asc()).all())

    series: dict[str, dict[str, list]] = {}
    for r in rows:
        series.setdefault(r.entity_id, {}).setdefault(r.metric_name, []).append(
            {"timestamp": r.timestamp.isoformat(), "value": r.value}
        )

    return {
        "site": {"id": site.id, "name": site.name, "region": site.region, "tier": site.tier, "extra": site.extra},
        "children": [{"id": c.id, "type": c.type, "name": c.name} for c in children],
        "series": series,
    }
