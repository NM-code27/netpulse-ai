"""Fault-scenario catalog: which fault types are valid on which entity types,
shared by the historical generator, the live scenario API, and demo tooling."""

FAULT_TYPES_BY_TARGET_TYPE = {
    "wan_link": ["link_degradation", "bandwidth_saturation"],
    "router": ["device_down"],
    "switch": ["device_down"],
    "dns_resolver": ["dns_failure"],
    "app_server": ["app_latency"],
}

SCENARIO_LABELS = {
    "link_degradation": "WAN link degradation",
    "bandwidth_saturation": "Bandwidth saturation",
    "device_down": "Device failure",
    "dns_failure": "DNS resolver failure",
    "app_latency": "Application tier latency spike",
}


def is_valid(entity_type: str, fault_type: str) -> bool:
    return fault_type in FAULT_TYPES_BY_TARGET_TYPE.get(entity_type, [])
