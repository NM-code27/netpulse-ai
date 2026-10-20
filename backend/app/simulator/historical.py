"""
Offline historical-data generator used for model training and backtesting
evaluation. Uses the exact same statistical model as the live simulator
(app/simulator/model.py) so models trained here transfer to the live demo.

Produces:
  app/ml/data/historical_metrics.parquet  -- long-format telemetry
  app/ml/data/historical_faults.json      -- ground-truth fault windows (for
                                              labeling and lead-time scoring)

Run: python -m app.simulator.historical
"""
import json
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

from app.data.topology_seed import TOPOLOGY
from app.simulator.model import simulate_tick, compose_site_app_response_time
from app.simulator.scenarios import FAULT_TYPES_BY_TARGET_TYPE

DATA_DIR = Path(__file__).resolve().parent.parent / "ml" / "data"


def generate_historical(days: int = 16, resolution_minutes: float = 2.0,
                         seed: int = 7, n_faults: int = 140, train_fraction: float = 0.75):
    """
    train_fraction controls where faults are scheduled: a `train_fraction`
    share are placed in the first part of the timeline and the rest in the
    final (1 - train_fraction) share. app/ml/train.py splits each entity's
    series chronologically at the same fraction, so this guarantees the test
    split actually contains held-out fault examples instead of leaving that
    to chance -- with only ~24 faults scattered uniformly across 7 days,
    random luck can (and did, in an earlier version of this script) put
    nearly all of them in the training period, leaving nothing to evaluate
    the risk classifiers against.
    """
    rng = random.Random(seed)
    entities = TOPOLOGY["entities"]
    sites = [e for e in entities if e["type"] == "site"]
    wan_link_by_site = {e["parent_id"]: e["id"] for e in entities if e["type"] == "wan_link"}
    dns_id = TOPOLOGY["dns_id"]
    app_tier_id = TOPOLOGY["app_tier_id"]

    total_minutes = days * 24 * 60
    n_ticks = int(total_minutes / resolution_minutes)
    cutoff_min = total_minutes * train_fraction

    # Group fault-capable entities by type and draw the TYPE uniformly first, then
    # an entity within that type. A plain rng.choice over all entities would pick
    # by raw count (20 routers vs. 1 DNS resolver), so the rare shared-service
    # faults (dns_failure, app_latency) would almost never be sampled -- and
    # those are exactly the faults that exercise the "shared service affects many
    # sites at once" root-cause story this project is built to demonstrate.
    by_type: dict[str, list] = {}
    for e in entities:
        if e["type"] in FAULT_TYPES_BY_TARGET_TYPE:
            by_type.setdefault(e["type"], []).append(e)
    entity_types = list(by_type.keys())

    n_test_faults = max(1, round(n_faults * (1 - train_fraction)))

    faults = []
    for i in range(n_faults):
        in_test = i < n_test_faults
        target_type = rng.choice(entity_types)
        target = rng.choice(by_type[target_type])
        fault_type = rng.choice(FAULT_TYPES_BY_TARGET_TYPE[target["type"]])
        duration = rng.uniform(25, 150)
        if in_test:
            region_start, region_end = cutoff_min + 30, total_minutes - duration - 30
        else:
            region_start, region_end = 60, cutoff_min - duration - 30
        region_end = max(region_end, region_start + 1)
        start = rng.uniform(region_start, region_end)
        faults.append({
            "entity_id": target["id"], "entity_type": target["type"], "fault_type": fault_type,
            "start_min": start, "end_min": start + duration,
        })

    faults_by_entity: dict[str, list] = {}
    for f in faults:
        faults_by_entity.setdefault(f["entity_id"], []).append(f)

    walks: dict[str, dict] = {}
    rows = []
    base_time = datetime.now(timezone.utc) - timedelta(minutes=total_minutes)

    for tick in range(n_ticks):
        elapsed = tick * resolution_minutes
        now = base_time + timedelta(minutes=elapsed)
        current_values: dict[str, dict] = {}

        for e in entities:
            if e["type"] == "site":
                continue
            active_fault = None
            for f in faults_by_entity.get(e["id"], []):
                if f["start_min"] <= elapsed <= f["end_min"]:
                    active_fault = {"fault_type": f["fault_type"],
                                     "elapsed_in_fault_min": elapsed - f["start_min"]}
                    break
            w = walks.setdefault(e["id"], {})
            values = simulate_tick(e["type"], elapsed, w, rng, active_fault)
            current_values[e["id"]] = values
            for metric_name, value in values.items():
                rows.append((e["id"], e["type"], metric_name, now, value))

        dns_time = current_values.get(dns_id, {}).get("resolution_time_ms", 8.0)
        app_time = current_values.get(app_tier_id, {}).get("response_time_ms", 90.0)

        for site in sites:
            wan_id = wan_link_by_site.get(site["id"])
            wan_latency = current_values.get(wan_id, {}).get("latency_ms", 25.0)
            w = walks.setdefault(site["id"], {})
            value = compose_site_app_response_time(elapsed, w, rng, wan_latency, dns_time, app_time)
            rows.append((site["id"], "site", "app_response_time_ms", now, round(value, 3)))

        if tick % 500 == 0:
            print(f"  tick {tick}/{n_ticks}", end="\r")

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(rows, columns=["entity_id", "entity_type", "metric_name", "timestamp", "value"])
    df.to_parquet(DATA_DIR / "historical_metrics.parquet", index=False)

    faults_out = [{
        **f,
        "start_time": (base_time + timedelta(minutes=f["start_min"])).isoformat(),
        "end_time": (base_time + timedelta(minutes=f["end_min"])).isoformat(),
    } for f in faults]
    with open(DATA_DIR / "historical_faults.json", "w") as fh:
        json.dump(faults_out, fh, indent=2)

    return df, faults_out


if __name__ == "__main__":
    df, faults = generate_historical()
    print(f"\nGenerated {len(df):,} rows across {df['entity_id'].nunique()} entities, "
          f"{len(faults)} fault windows -> {DATA_DIR}")
