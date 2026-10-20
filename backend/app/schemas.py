from datetime import datetime

from pydantic import BaseModel


class EntityOut(BaseModel):
    id: str
    type: str
    name: str
    region: str | None = None
    tier: str | None = None
    parent_id: str | None = None
    extra: dict = {}

    class Config:
        from_attributes = True


class MetricPoint(BaseModel):
    timestamp: datetime
    value: float


class MetricSeriesOut(BaseModel):
    entity_id: str
    metric_name: str
    points: list[MetricPoint]


class AlertOut(BaseModel):
    id: int
    created_at: datetime
    entity_id: str
    alert_type: str
    severity: str
    metric_name: str | None = None
    risk_score: float | None = None
    lead_time_minutes: float | None = None
    message: str
    root_cause: dict | None = None
    business_impact: dict | None = None
    scenario_id: str | None = None
    resolved: bool

    class Config:
        from_attributes = True


class ScenarioCreate(BaseModel):
    fault_type: str
    target_entity_id: str


class ScenarioOut(BaseModel):
    id: str
    name: str
    fault_type: str
    target_entity_id: str
    status: str
    started_at: datetime
    ended_at: datetime | None = None

    class Config:
        from_attributes = True


class AssistantRequest(BaseModel):
    alert_id: int


class AssistantResponse(BaseModel):
    text: str
    source: str
    evidence: dict
