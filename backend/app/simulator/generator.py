"""
Live simulator: ticks in real time inside the FastAPI process (see
app/worker.py), writing fresh telemetry into the metrics table every
`settings.simulator_tick_seconds` and respecting whatever fault scenario
is currently active in the `scenarios` table.
"""
import random
import time
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.config import settings
from app.db.models import Entity, Metric, Scenario
from app.simulator.model import simulate_tick, compose_site_app_response_time


class SimulatorEngine:
    def __init__(self):
        self.start_time = time.monotonic()
        self.rng = random.Random()
        self.walks: dict[str, dict] = {}

    def elapsed_minutes(self) -> float:
        return (time.monotonic() - self.start_time) / 60.0 * settings.live_speed_multiplier

    def _active_fault_for(self, entity_id: str, scenarios: list[Scenario], now: datetime) -> dict | None:
        for s in scenarios:
            if s.target_entity_id == entity_id and s.status == "running":
                real_elapsed = (now - s.started_at.replace(tzinfo=timezone.utc)).total_seconds() / 60.0
                return {"fault_type": s.fault_type, "elapsed_in_fault_min": real_elapsed * settings.live_speed_multiplier}
        return None

    def tick(self, db: Session):
        now = datetime.now(timezone.utc)
        elapsed = self.elapsed_minutes()
        running_scenarios = db.query(Scenario).filter(Scenario.status == "running").all()

        entities = db.query(Entity).all()
        by_id = {e.id: e for e in entities}
        sites = [e for e in entities if e.type == "site"]
        rows = []

        current_values: dict[str, dict] = {}  # entity_id -> {metric_name: value}

        for e in entities:
            if e.type == "site":
                continue
            fault = self._active_fault_for(e.id, running_scenarios, now)
            walks = self.walks.setdefault(e.id, {})
            values = simulate_tick(e.type, elapsed, walks, self.rng, fault)
            current_values[e.id] = values
            for metric_name, value in values.items():
                rows.append(Metric(entity_id=e.id, metric_name=metric_name, timestamp=now, value=value))

        dns_id = next((e.id for e in entities if e.type == "dns_resolver"), None)
        app_tier_id = next((e.id for e in entities if e.type == "app_server"), None)
        dns_time = current_values.get(dns_id, {}).get("resolution_time_ms", 8.0)
        app_time = current_values.get(app_tier_id, {}).get("response_time_ms", 90.0)

        wan_link_by_site = {
            e.parent_id: e.id for e in entities if e.type == "wan_link"
        }

        for site in sites:
            wan_id = wan_link_by_site.get(site.id)
            wan_latency = current_values.get(wan_id, {}).get("latency_ms", 25.0)
            fault = self._active_fault_for(site.id, running_scenarios, now)  # rare: direct site-level fault
            walks = self.walks.setdefault(site.id, {})
            value = compose_site_app_response_time(elapsed, walks, self.rng, wan_latency, dns_time, app_time)
            if fault and fault["fault_type"] == "app_latency":
                value += 200.0  # direct site-targeted app incident, independent of shared app tier
            current_values[site.id] = {"app_response_time_ms": value}
            rows.append(Metric(entity_id=site.id, metric_name="app_response_time_ms", timestamp=now, value=round(value, 3)))

        db.bulk_save_objects(rows)
        db.commit()
        return {"timestamp": now.isoformat(), "rows_written": len(rows)}
