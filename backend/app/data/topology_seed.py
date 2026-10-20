"""
Deterministic synthetic topology for NetPulse AI.

Models a mid-size enterprise: one HQ/datacenter hub plus 20 branch offices,
each connected to the hub over a WAN link, each running a small set of LAN
devices, and all sharing two hub-side services (DNS resolution and a core
application tier) that can independently fail and affect many sites at once.
This fan-in/fan-out shape is what makes root-cause correlation meaningful:
a single WAN link failing only hurts one site, but a shared DNS or app-tier
failure hurts many sites simultaneously, and the correlation engine has to
tell those apart from topology alone.
"""
import random

REGIONS = ["US-East", "US-West", "US-Central", "EU-West", "EU-North", "APAC"]
BUSINESS_APPS = ["ERP", "CRM", "VoIP", "Order-Processing", "Payroll", "Support-Portal"]

BRANCH_NAMES = [
    "New York", "Chicago", "Dallas", "Atlanta", "Denver", "Seattle",
    "Boston", "Miami", "Phoenix", "Minneapolis", "London", "Dublin",
    "Berlin", "Amsterdam", "Paris", "Singapore", "Tokyo", "Sydney",
    "Toronto", "Austin",
]

TIER_BY_USERS = [
    (300, "critical"),
    (120, "high"),
    (40, "standard"),
]


def _tier_for(users: int) -> str:
    for threshold, tier in TIER_BY_USERS:
        if users >= threshold:
            return tier
    return "low"


def build_topology(seed: int = 42) -> dict:
    rng = random.Random(seed)

    entities = []
    links = []

    hub_id = "site-hq"
    entities.append({
        "id": hub_id,
        "type": "site",
        "name": "HQ Datacenter",
        "region": "US-East",
        "tier": "critical",
        "users": 900,
        "apps": BUSINESS_APPS,
        "parent_id": None,
    })

    # Hub-side shared services: any site's traffic can be hurt by either of these.
    dns_id = "svc-dns"
    entities.append({
        "id": dns_id, "type": "dns_resolver", "name": "Core DNS Resolver",
        "region": "US-East", "tier": "critical", "users": None, "apps": None,
        "parent_id": hub_id,
    })

    app_tier_id = "svc-apptier"
    entities.append({
        "id": app_tier_id, "type": "app_server", "name": "Core Application Tier",
        "region": "US-East", "tier": "critical", "users": None, "apps": BUSINESS_APPS,
        "parent_id": hub_id,
    })

    for i, name in enumerate(BRANCH_NAMES, start=1):
        site_id = f"site-{i:02d}"
        users = rng.choice([35, 60, 90, 140, 180, 260, 340, 420])
        apps = rng.sample(BUSINESS_APPS, k=rng.randint(2, 4))
        region = rng.choice(REGIONS)
        tier = _tier_for(users)

        entities.append({
            "id": site_id, "type": "site", "name": f"{name} Branch",
            "region": region, "tier": tier, "users": users, "apps": apps,
            "parent_id": None,
        })

        wan_id = f"link-wan-{i:02d}"
        bandwidth = rng.choice([100, 200, 500, 1000])
        links.append({
            "id": wan_id, "type": "wan_link", "name": f"{name} WAN Uplink",
            "site_id": site_id, "connects_to": hub_id,
            "bandwidth_mbps": bandwidth, "parent_id": site_id,
        })
        entities.append({
            "id": wan_id, "type": "wan_link", "name": f"{name} WAN Uplink",
            "region": region, "tier": tier, "users": None, "apps": None,
            "parent_id": site_id,
        })

        router_id = f"dev-rtr-{i:02d}"
        entities.append({
            "id": router_id, "type": "router", "name": f"{name} Edge Router",
            "region": region, "tier": tier, "users": None, "apps": None,
            "parent_id": site_id,
        })

        switch_id = f"dev-sw-{i:02d}"
        entities.append({
            "id": switch_id, "type": "switch", "name": f"{name} Access Switch",
            "region": region, "tier": tier, "users": None, "apps": None,
            "parent_id": site_id,
        })

    return {"entities": entities, "links": links, "hub_id": hub_id,
            "dns_id": dns_id, "app_tier_id": app_tier_id}


TOPOLOGY = build_topology()

if __name__ == "__main__":
    import json
    print(json.dumps(TOPOLOGY, indent=2))
