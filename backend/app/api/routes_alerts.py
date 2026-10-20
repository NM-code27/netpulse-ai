from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.models import Alert
from app.db.session import get_db
from app.schemas import AlertOut

router = APIRouter(prefix="/api/alerts", tags=["alerts"])


@router.get("", response_model=list[AlertOut])
def list_alerts(resolved: bool | None = None, limit: int = 50, db: Session = Depends(get_db)):
    q = db.query(Alert)
    if resolved is not None:
        q = q.filter(Alert.resolved == resolved)
    return q.order_by(Alert.created_at.desc()).limit(limit).all()


@router.post("/{alert_id}/resolve", response_model=AlertOut)
def resolve_alert(alert_id: int, db: Session = Depends(get_db)):
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if alert:
        alert.resolved = True
        db.commit()
    return alert
