"""
Rule-based correlation on top of ML anomaly scores: given a site whose
app_response_time_ms looks degraded, decide whether the likely cause is its
own WAN link, one of its own devices, the shared DNS resolver, or the shared
application tier -- using exactly the fan-in/fan-out shape built into the
topology (see app/data/topology_seed.py): a shared-service fault shows up on
MANY sites at once, a link/device fault shows up in isolation.

Used identically by the live alerting path (app/worker.py, against a
real-time snapshot of anomaly scores) and by training-time evaluation
(app/ml/train.py, against a snapshot reconstructed at each historical
fault's peak) -- that's what makes the top-1/top-3 root-cause accuracy
metric in the training report meaningful.
"""
from app.data.topology_seed import TOPOLOGY

AFFECTED_THRESHOLD = 40.0  # anomaly score above which a site counts as "affected" for fan-out purposes


def _build_topology_index():
    entities = TOPOLOGY["entities"]
    by_id = {e["id"]: e for e in entities}
    sites = [e["id"] for e in entities if e["type"] == "site"]
    wan_by_site = {e["parent_id"]: e["id"] for e in entities if e["type"] == "wan_link"}
    router_by_site = {e["parent_id"]: e["id"] for e in entities if e["type"] == "router"}
    switch_by_site = {e["parent_id"]: e["id"] for e in entities if e["type"] == "switch"}
    return {
        "by_id": by_id, "sites": sites, "wan_by_site": wan_by_site,
        "router_by_site": router_by_site, "switch_by_site": switch_by_site,
        "dns_id": TOPOLOGY["dns_id"], "app_tier_id": TOPOLOGY["app_tier_id"],
    }


TOPO_INDEX = _build_topology_index()


def _score(snapshot: dict, entity_id: str | None, metric_name: str) -> float:
    if entity_id is None:
        return 0.0
    return float(snapshot.get(entity_id, {}).get(metric_name, 0.0) or 0.0)


def analyze_root_cause(site_id: str, snapshot: dict, topo: dict = TOPO_INDEX) -> list[dict]:
    """
    snapshot: {entity_id: {metric_name: anomaly_score_0_100}} for every
    entity at one point in time. Returns candidates sorted by score desc,
    each with a 0-100 confidence (candidates sum to 100).
    """
    wan_id = topo["wan_by_site"].get(site_id)
    router_id = topo["router_by_site"].get(site_id)
    switch_id = topo["switch_by_site"].get(site_id)
    dns_id = topo["dns_id"]
    app_id = topo["app_tier_id"]

    wan_score = max(
        _score(snapshot, wan_id, "latency_ms"), _score(snapshot, wan_id, "packet_loss_pct"),
        _score(snapshot, wan_id, "jitter_ms"), _score(snapshot, wan_id, "bandwidth_util_pct"),
    )
    router_score = _score(snapshot, router_id, "cpu_pct")
    switch_score = _score(snapshot, switch_id, "cpu_pct")
    device_score = max(router_score, switch_score)
    device_entity = router_id if router_score >= switch_score else switch_id
    dns_score = _score(snapshot, dns_id, "resolution_time_ms")
    app_score = _score(snapshot, app_id, "response_time_ms")

    other_sites = [s for s in topo["sites"] if s != site_id]
    affected_other = sum(1 for s in other_sites if _score(snapshot, s, "app_response_time_ms") > AFFECTED_THRESHOLD)
    fan_out = affected_other / max(1, len(other_sites))

    candidates = [
        {"category": "wan_link", "entity_id": wan_id, "label": "WAN link degradation",
         "score": wan_score * (1 - fan_out)},
        {"category": "device", "entity_id": device_entity, "label": "Site device issue (router/switch)",
         "score": device_score * (1 - fan_out)},
        {"category": "dns", "entity_id": dns_id, "label": "Shared DNS resolver issue",
         "score": dns_score * (0.25 + 0.75 * fan_out)},
        {"category": "app_tier", "entity_id": app_id, "label": "Shared application-tier issue",
         "score": app_score * (0.25 + 0.75 * fan_out)},
    ]
    total = sum(c["score"] for c in candidates) or 1.0
    for c in candidates:
        c["confidence"] = round(100.0 * c["score"] / total, 1)
    candidates.sort(key=lambda c: c["score"], reverse=True)
    return candidates


def category_for_fault_type(fault_type: str) -> str:
    return {
        "link_degradation": "wan_link", "bandwidth_saturation": "wan_link",
        "device_down": "device", "dns_failure": "dns", "app_latency": "app_tier",
    }[fault_type]
