from app.ml.root_cause import analyze_root_cause, category_for_fault_type


def test_isolated_wan_link_anomaly_ranks_wan_link_top():
    snapshot = {
        "link-wan-01": {"latency_ms": 90.0, "packet_loss_pct": 10.0},
        "dev-rtr-01": {"cpu_pct": 5.0},
        "dev-sw-01": {"cpu_pct": 5.0},
        "svc-dns": {"resolution_time_ms": 2.0},
        "svc-apptier": {"response_time_ms": 3.0},
    }
    candidates = analyze_root_cause("site-01", snapshot)
    assert candidates[0]["category"] == "wan_link"


def test_shared_dns_anomaly_with_fanout_ranks_dns_top():
    snapshot = {"svc-dns": {"resolution_time_ms": 95.0}}
    for i in range(1, 21):
        snapshot[f"site-{i:02d}"] = {"app_response_time_ms": 85.0}
    candidates = analyze_root_cause("site-01", snapshot)
    assert candidates[0]["category"] == "dns"


def test_category_for_fault_type_mapping():
    assert category_for_fault_type("link_degradation") == "wan_link"
    assert category_for_fault_type("device_down") == "device"
    assert category_for_fault_type("dns_failure") == "dns"
    assert category_for_fault_type("app_latency") == "app_tier"
