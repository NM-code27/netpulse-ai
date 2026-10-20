from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.models import Entity
from app.db.session import get_db
from app.schemas import EntityOut

router = APIRouter(prefix="/api/topology", tags=["topology"])


@router.get("", response_model=list[EntityOut])
def get_topology(db: Session = Depends(get_db)):
    return db.query(Entity).all()
