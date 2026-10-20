from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.assistant.agent import explain
from app.db.models import Alert, Entity, Metric
from app.db.session import get_db
from app.schemas import AssistantRequest, AssistantResponse

router = APIRouter(prefix="/api/assistant", tags=["assistant"])


@router.post("/explain", response_model=AssistantResponse)
def explain_alert(payload: AssistantRequest, db: Session = Depends(get_db)):
    alert = db.query(Alert).filter(Alert.id == payload.alert_id).first()
    if not alert:
        raise HTTPException(404, "alert not found")

    entity = db.query(Entity).filter(Entity.id == alert.entity_id).first()
    site = entity
    if entity and entity.type != "site" and entity.parent_id:
        site = db.query(Entity).filter(Entity.id == entity.parent_id).first() or entity

    latest = (db.query(Metric)
              .filter(Metric.entity_id == alert.entity_id, Metric.metric_name == alert.metric_name)
              .order_by(Metric.timestamp.desc()).first())

    root_cause = (alert.root_cause or {}).get("candidates", [])
    evidence = {
        "site_id": site.id if site else alert.entity_id,
        "site_name": site.name if site else alert.entity_id,
        "metric_name": alert.metric_name,
        "current_value": latest.value if latest else None,
        "risk_score": alert.risk_score,
        "anomaly_score": (alert.root_cause or {}).get("anomaly_score"),
        "lead_time_minutes": alert.lead_time_minutes,
        "root_cause": root_cause,
        "business_impact": alert.business_impact or {},
    }

    result = explain(evidence)
    return AssistantResponse(text=result["text"], source=result["source"], evidence=evidence)
