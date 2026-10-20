"""
Statistical model behind every metric NetPulse AI collects.

Shared by the live simulator (app/simulator/generator.py, ticking in real
time against the running API) and the offline historical generator
(app/simulator/historical.py, used to produce training/backtest data). Both
call `simulate_tick()` so the live demo and the offline-trained models are
drawn from the same distribution.

Design: each metric has a diurnal baseline (business-hours load curve) plus
autocorrelated noise (a random walk, not independent noise each tick, since
real network metrics drift rather than jump). Active fault scenarios apply a
time-shaped penalty on top of the baseline -- ramping in, holding, and
(if not left to actually breach) ramping back out.
"""
import math
from dataclasses import dataclass, field


def diurnal_multiplier(elapsed_minutes: float) -> float:
    """Business-hours load curve: low overnight, peaks ~midday, 24h period."""
    hour_of_day = (elapsed_minutes / 60.0) % 24.0
    # Peak at hour 13, trough at hour 1, smooth cosine.
    return 0.55 + 0.45 * math.cos((hour_of_day - 13.0) / 24.0 * 2 * math.pi)


@dataclass
class WalkState:
    """Per-(entity, metric) autocorrelated noise state, so values drift smoothly."""
    value: float = 0.0

    def step(self, rng, volatility: float, pull: float = 0.08) -> float:
        self.value += rng.gauss(0, volatility) - pull * self.value
        return self.value


BASELINES = {
    "wan_link": {
        "latency_ms": dict(base=25.0, diurnal_amp=10.0, volatility=0.8),
        "packet_loss_pct": dict(base=0.05, diurnal_amp=0.03, volatility=0.01),
        "jitter_ms": dict(base=2.0, diurnal_amp=1.0, volatility=0.15),
        "bandwidth_util_pct": dict(base=25.0, diurnal_amp=35.0, volatility=1.5),
    },
    "router": {
        "cpu_pct": dict(base=20.0, diurnal_amp=20.0, volatility=1.2),
    },
    "switch": {
        "cpu_pct": dict(base=15.0, diurnal_amp=15.0, volatility=1.0),
    },
    "dns_resolver": {
        "resolution_time_ms": dict(base=8.0, diurnal_amp=3.0, volatility=0.4),
    },
    "app_server": {
        "response_time_ms": dict(base=90.0, diurnal_amp=40.0, volatility=3.0),
        "cpu_pct": dict(base=30.0, diurnal_amp=25.0, volatility=1.5),
    },
    "site": {
        "app_response_time_ms": dict(base=110.0, diurnal_amp=30.0, volatility=2.5),
    },
}

FLOORS = {
    "latency_ms": 2.0, "packet_loss_pct": 0.0, "jitter_ms": 0.1,
    "bandwidth_util_pct": 1.0, "cpu_pct": 2.0, "resolution_time_ms": 1.0,
    "response_time_ms": 10.0, "app_response_time_ms": 15.0,
}
CEILINGS = {
    "packet_loss_pct": 100.0, "bandwidth_util_pct": 100.0, "cpu_pct": 100.0,
}


def _bounded(metric_name: str, value: float) -> float:
    value = max(value, FLOORS.get(metric_name, 0.0))
    if metric_name in CEILINGS:
        value = min(value, CEILINGS[metric_name])
    return value


def fault_shape(elapsed_in_fault_min: float, ramp_min: float, hold_min: float) -> float:
    """0->1->1...->1 ramp-in then hold (faults are ended explicitly, not auto-decayed)."""
    if elapsed_in_fault_min <= 0:
        return 0.0
    if elapsed_in_fault_min < ramp_min:
        return elapsed_in_fault_min / ramp_min
    return 1.0


# intensity: multiplicative/additive penalties applied to each affected metric at full ramp
FAULT_EFFECTS = {
    "link_degradation": {
        "latency_ms": ("add_mult", 120.0),
        "packet_loss_pct": ("add_mult", 8.0),
        "jitter_ms": ("add_mult", 15.0),
    },
    "bandwidth_saturation": {
        "bandwidth_util_pct": ("add_mult", 70.0),
        "latency_ms": ("add_mult", 60.0),
        "jitter_ms": ("add_mult", 6.0),
    },
    "device_down": {
        "cpu_pct": ("set", 0.0),
        "status": ("set", 0.0),
    },
    "dns_failure": {
        "resolution_time_ms": ("add_mult", 400.0),
    },
    "app_latency": {
        "response_time_ms": ("add_mult", 300.0),
        "cpu_pct": ("add_mult", 45.0),
    },
}

RAMP_MINUTES = {
    "link_degradation": 12.0, "bandwidth_saturation": 8.0, "device_down": 0.5,
    "dns_failure": 2.0, "app_latency": 6.0,
}


def expected_baseline(entity_type: str, metric_name: str, elapsed_minutes: float) -> float:
    spec = BASELINES[entity_type][metric_name]
    return spec["base"] + spec["diurnal_amp"] * diurnal_multiplier(elapsed_minutes)


def compose_site_app_response_time(elapsed_minutes: float, walks: dict, rng,
                                    wan_latency_ms: float, dns_resolution_ms: float,
                                    app_tier_response_ms: float) -> float:
    """
    A site's perceived application latency is not independent: it rides on
    top of its own WAN link, the shared DNS resolver, and the shared app
    tier. Whichever of those three is running hot beyond ITS OWN baseline
    leaks into every site's app_response_time_ms -- which is exactly the
    signal the root-cause engine uses to tell "my WAN link is bad" apart
    from "DNS is down for everyone" apart from "the app tier is overloaded".
    """
    spec = BASELINES["site"]["app_response_time_ms"]
    walk = walks.setdefault("app_response_time_ms", WalkState())
    noise = walk.step(rng, spec["volatility"])
    diurnal = diurnal_multiplier(elapsed_minutes)
    base_value = spec["base"] + spec["diurnal_amp"] * diurnal + noise

    wan_delta = max(0.0, wan_latency_ms - expected_baseline("wan_link", "latency_ms", elapsed_minutes))
    dns_delta = max(0.0, dns_resolution_ms - expected_baseline("dns_resolver", "resolution_time_ms", elapsed_minutes))
    app_delta = max(0.0, app_tier_response_ms - expected_baseline("app_server", "response_time_ms", elapsed_minutes))

    value = base_value + 0.9 * wan_delta + 1.1 * dns_delta + 0.7 * app_delta
    return round(_bounded("app_response_time_ms", value), 3)


def simulate_tick(entity_type: str, elapsed_minutes: float, walks: dict, rng,
                   active_fault: dict | None = None) -> dict:
    """
    Returns {metric_name: value} for one entity at one point in time.
    Not used for entity_type "site" -- see compose_site_app_response_time,
    which needs sibling entities' values rather than just this entity's own.

    walks: dict of WalkState keyed by metric_name, persisted by the caller
           across ticks for this entity (so noise is autocorrelated).
    active_fault: {"fault_type": str, "elapsed_in_fault_min": float} or None.
    """
    specs = BASELINES.get(entity_type, {})
    out = {}
    diurnal = diurnal_multiplier(elapsed_minutes)

    for metric_name, spec in specs.items():
        walk = walks.setdefault(metric_name, WalkState())
        noise = walk.step(rng, spec["volatility"])
        value = spec["base"] + spec["diurnal_amp"] * diurnal + noise

        if active_fault:
            effect = FAULT_EFFECTS.get(active_fault["fault_type"], {}).get(metric_name)
            if effect:
                kind, magnitude = effect
                ramp = RAMP_MINUTES.get(active_fault["fault_type"], 5.0)
                shape = fault_shape(active_fault["elapsed_in_fault_min"], ramp, hold_min=1e9)
                if kind == "add_mult":
                    value += magnitude * shape
                elif kind == "set" and shape >= 1.0:
                    value = magnitude

        out[metric_name] = round(_bounded(metric_name, value), 3)

    if entity_type in ("router", "switch"):
        status_walk = walks.setdefault("status", WalkState())
        down = bool(active_fault and active_fault["fault_type"] == "device_down"
                    and fault_shape(active_fault["elapsed_in_fault_min"],
                                     RAMP_MINUTES["device_down"], 1e9) >= 1.0)
        out["status"] = 0.0 if down else 1.0

    return out
