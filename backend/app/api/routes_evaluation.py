import json
from pathlib import Path

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/api/evaluation", tags=["evaluation"])

REPORT_PATH = Path(__file__).resolve().parent.parent / "ml" / "artifacts" / "training_report.json"


@router.get("")
def get_evaluation():
    if not REPORT_PATH.exists():
        raise HTTPException(404, "No training report yet -- run `python -m app.ml.train` first")
    with open(REPORT_PATH) as f:
        return json.load(f)
