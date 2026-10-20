import json
from pathlib import Path

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/api/realworld", tags=["realworld"])

DATA_DIR = Path(__file__).resolve().parent.parent / "realworld" / "data"


@router.get("")
def get_realworld_validation():
    path = DATA_DIR / "validation_report.json"
    if not path.exists():
        raise HTTPException(
            404, "No real-world data fetched yet -- run `python -m app.realworld.fetch_ripe_atlas` "
                 "then `python -m app.realworld.validate` on the backend",
        )
    with open(path) as f:
        return json.load(f)
