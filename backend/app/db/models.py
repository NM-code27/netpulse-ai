from sqlalchemy import Column, String, Float, Integer, DateTime, Boolean, JSON, ForeignKey, Index
from sqlalchemy.sql import func

from app.db.session import Base


class Entity(Base):
    """Every node in the topology: sites, WAN links, routers, switches, DNS, app tier."""
    __tablename__ = "entities"

    id = Column(String, primary_key=True)
    type = Column(String, index=True)       # site | wan_link | router | switch | dns_resolver | app_server
    name = Column(String)
    region = Column(String, index=True)
    tier = Column(String, index=True)       # critical | high | standard | low
    parent_id = Column(String, ForeignKey("entities.id"), nullable=True, index=True)
    extra = Column(JSON, default=dict)      # users, apps, bandwidth_mbps, connects_to, etc.


class Metric(Base):
    """Narrow time-series table: one row per (entity, metric, timestamp)."""
    __tablename__ = "metrics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    entity_id = Column(String, ForeignKey("entities.id"), index=True)
    metric_name = Column(String, index=True)   # latency_ms, packet_loss_pct, jitter_ms, bandwidth_util_pct,
                                                # cpu_pct, status, resolution_time_ms, response_time_ms
    timestamp = Column(DateTime(timezone=True), index=True)
    value = Column(Float)

    __table_args__ = (
        Index("ix_metrics_entity_metric_ts", "entity_id", "metric_name", "timestamp"),
    )


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    entity_id = Column(String, ForeignKey("entities.id"), index=True)
    alert_type = Column(String)             # anomaly | predictive_risk
    severity = Column(String)               # info | warning | critical
    metric_name = Column(String, nullable=True)
    risk_score = Column(Float, nullable=True)        # 0-100 outage-risk score
    lead_time_minutes = Column(Float, nullable=True) # forecast lead time before breach
    message = Column(String)
    root_cause = Column(JSON, nullable=True)         # {category, confidence, evidence:[...], top3:[...]}
    business_impact = Column(JSON, nullable=True)    # {users_affected, sites_affected, apps_affected}
    scenario_id = Column(String, nullable=True, index=True)
    resolved = Column(Boolean, default=False)


class Scenario(Base):
    __tablename__ = "scenarios"

    id = Column(String, primary_key=True)
    name = Column(String)
    fault_type = Column(String)   # link_degradation | device_down | dns_failure | bandwidth_saturation | app_latency
    target_entity_id = Column(String, ForeignKey("entities.id"))
    status = Column(String, default="running")   # running | completed
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    ended_at = Column(DateTime(timezone=True), nullable=True)
    params = Column(JSON, default=dict)
