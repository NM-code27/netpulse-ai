import random

from app.simulator.model import simulate_tick, compose_site_app_response_time


def test_simulate_tick_wan_link_baseline_in_range():
    rng = random.Random(1)
    walks = {}
    values = simulate_tick("wan_link", elapsed_minutes=600, walks=walks, rng=rng)
    assert "latency_ms" in values
    assert "packet_loss_pct" in values
    assert values["latency_ms"] > 0
    assert 0 <= values["packet_loss_pct"] <= 100


def test_simulate_tick_link_degradation_raises_latency():
    rng = random.Random(2)
    walks_normal, walks_fault = {}, {}
    normal = simulate_tick("wan_link", 600, walks_normal, rng)
    fault = simulate_tick("wan_link", 600, walks_fault, rng,
                           active_fault={"fault_type": "link_degradation", "elapsed_in_fault_min": 30})
    assert fault["latency_ms"] > normal["latency_ms"]


def test_device_down_sets_status_zero():
    rng = random.Random(3)
    walks = {}
    values = simulate_tick("router", 600, walks, rng,
                            active_fault={"fault_type": "device_down", "elapsed_in_fault_min": 10})
    assert values["status"] == 0.0


def test_compose_site_app_response_time_rises_with_dns_delay():
    rng = random.Random(4)
    walks = {}
    baseline = compose_site_app_response_time(600, {}, rng, wan_latency_ms=25.0,
                                                dns_resolution_ms=8.0, app_tier_response_ms=90.0)
    degraded = compose_site_app_response_time(600, walks, rng, wan_latency_ms=25.0,
                                                dns_resolution_ms=400.0, app_tier_response_ms=90.0)
    assert degraded > baseline
