"""
Estimates who is actually affected by a given alert, based on documented
topology assumptions (app/data/topology_seed.py): site user counts and the
business apps each site depends on. A shared-service root cause (DNS or
app tier) fans out to every site currently showing a degraded
app_response_time_ms; a WAN-link or device root cause stays scoped to its
own site.
"""
from app.data.topology_seed import TOPOLOGY
from app.ml.root_cause import AFFECTED_THRESHOLD

ENTITY_BY_ID = {e["id"]: e for e in TOPOLOGY["entities"]}
SITES = [e for e in TOPOLOGY["entities"] if e["type"] == "site"]


def estimate_impact(root_cause_category: str, site_id: str, snapshot: dict) -> dict:
    if root_cause_category in ("dns", "app_tier"):
        affected = [s for s in SITES if snapshot.get(s["id"], {}).get("app_response_time_ms", 0) > AFFECTED_THRESHOLD]
        if site_id not in {s["id"] for s in affected} and site_id in ENTITY_BY_ID:
            affected.append(ENTITY_BY_ID[site_id])
    else:
        affected = [ENTITY_BY_ID[site_id]] if site_id in ENTITY_BY_ID else []

    users = sum((s.get("users") or 0) for s in affected)
    apps = sorted({a for s in affected for a in (s.get("apps") or [])})
    tiers = {s.get("tier") for s in affected}
    severity_tier = "critical" if "critical" in tiers else ("high" if "high" in tiers else "standard")

    return {
        "sites_affected": [s["id"] for s in affected],
        "site_names": [s["name"] for s in affected],
        "users_affected": users,
        "apps_affected": apps,
        "severity_tier": severity_tier,
    }
