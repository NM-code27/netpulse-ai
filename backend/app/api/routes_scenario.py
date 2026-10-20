import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.models import Entity, Scenario
from app.db.session import get_db
from app.schemas import ScenarioCreate, ScenarioOut
from app.simulator.scenarios import SCENARIO_LABELS, is_valid

router = APIRouter(prefix="/api/scenarios", tags=["scenarios"])


@router.get("", response_model=list[ScenarioOut])
def list_scenarios(db: Session = Depends(get_db)):
    return db.query(Scenario).order_by(Scenario.started_at.desc()).limit(50).all()


@router.post("", response_model=ScenarioOut)
def start_scenario(payload: ScenarioCreate, db: Session = Depends(get_db)):
    target = db.query(Entity).filter(Entity.id == payload.target_entity_id).first()
    if not target:
        raise HTTPException(404, "target_entity_id not found")
    if not is_valid(target.type, payload.fault_type):
        raise HTTPException(400, f"fault_type '{payload.fault_type}' not valid for entity type '{target.type}'")

    already_running = db.query(Scenario).filter(
        Scenario.target_entity_id == target.id, Scenario.status == "running"
    ).first()
    if already_running:
        raise HTTPException(409, "A scenario is already running on this entity")

    scenario = Scenario(
        id=str(uuid.uuid4()), name=f"{SCENARIO_LABELS[payload.fault_type]} -- {target.name}",
        fault_type=payload.fault_type, target_entity_id=target.id, status="running",
    )
    db.add(scenario)
    db.commit()
    db.refresh(scenario)
    return scenario


@router.post("/{scenario_id}/stop", response_model=ScenarioOut)
def stop_scenario(scenario_id: str, db: Session = Depends(get_db)):
    scenario = db.query(Scenario).filter(Scenario.id == scenario_id).first()
    if not scenario:
        raise HTTPException(404, "not found")
    scenario.status = "completed"
    scenario.ended_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(scenario)
    return scenario
