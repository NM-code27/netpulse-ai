"""
Pulls genuinely real internet measurement data from RIPE Atlas's public API
-- no account, no API key required. These are real, continuously-running
measurements RIPE NCC has operated since 2010, pinging real DNS root servers
from thousands of real distributed probes worldwide.

This is NOT a replacement for the synthetic enterprise simulator (there is
no public source of labeled, 20-branch-office network fault data -- that's
exactly why the simulator exists). It's a separate, honest validation
signal: real-world latency data used to (a) sanity-check that the
simulator's statistical shape (diurnal swing, noise envelope) is realistic,
and (b) show how the trained forecasting model performs on a real time
series it never trained on.

Measurement IDs 1001 and 1004 are RIPE Atlas "built-in" measurements:
  1001 -> ping to k.root-servers.net
  1004 -> ping to f.root-servers.net
Both public, both running continuously since 2010.

Run: python -m app.realworld.fetch_ripe_atlas
"""
import json
import time
from collections import defaultdict
from pathlib import Path
from statistics import mean, median

import httpx

DATA_DIR = Path(__file__).resolve().parent / "data"
BUCKET_SECONDS = 600  # 10-minute aggregation buckets

MEASUREMENTS = {
    "1001": {"id": 1001, "target": "k.root-servers.net", "label": "RIPE Atlas -> k-root DNS (global)"},
    "1004": {"id": 1004, "target": "f.root-servers.net", "label": "RIPE Atlas -> f-root DNS (global)"},
}


PROBE_SAMPLE_SIZE = 25  # a full unfiltered pull is tens of millions of rows -- RIPE Atlas has
                        # thousands of active probes on these measurements. Sampling a fixed set
                        # of real probes keeps this fast while still being genuinely real,
                        # geographically distributed multi-probe data.


def discover_active_probes(measurement_id: int, client: httpx.Client, sample_minutes: int = 15) -> list[int]:
    """Real probe IDs currently reporting on this measurement, found via a short recent window."""
    now = int(time.time())
    url = f"https://atlas.ripe.net/api/v2/measurements/{measurement_id}/results/"
    resp = client.get(url, params={"format": "json", "start": now - sample_minutes * 60, "stop": now})
    resp.raise_for_status()
    probe_ids = sorted({r["prb_id"] for r in resp.json() if "prb_id" in r})
    return probe_ids[:PROBE_SAMPLE_SIZE]


def fetch_measurement(measurement_id: int, hours: int = 48) -> list[dict]:
    now = int(time.time())
    start = now - hours * 3600
    url = f"https://atlas.ripe.net/api/v2/measurements/{measurement_id}/results/"
    with httpx.Client(timeout=90.0) as client:
        probe_ids = discover_active_probes(measurement_id, client)
        print(f"  sampling {len(probe_ids)} real active probes: {probe_ids}")
        resp = client.get(url, params={
            "format": "json", "start": start, "stop": now,
            "probe_ids": ",".join(str(p) for p in probe_ids),
        })
        resp.raise_for_status()
        results = resp.json()
    return results


def aggregate_to_buckets(raw_results: list[dict]) -> list[dict]:
    """Collapse thousands of individual real-probe pings into 10-minute
    mean/median/p95 RTT buckets -- usable for charting and as a model input
    series, and small enough to commit to the repo."""
    buckets: dict[int, list[float]] = defaultdict(list)
    for r in raw_results:
        avg = r.get("avg")
        ts = r.get("timestamp")
        if avg is None or avg < 0 or ts is None:
            continue
        bucket = (ts // BUCKET_SECONDS) * BUCKET_SECONDS
        buckets[bucket].append(avg)

    out = []
    for bucket_ts in sorted(buckets):
        vals = sorted(buckets[bucket_ts])
        n = len(vals)
        out.append({
            "timestamp": bucket_ts,
            "mean_rtt_ms": round(mean(vals), 3),
            "median_rtt_ms": round(median(vals), 3),
            "p95_rtt_ms": round(vals[int(n * 0.95)] if n > 1 else vals[0], 3),
            "sample_count": n,
        })
    return out


def fetch_all(hours: int = 48):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    manifest = {}
    for key, meta in MEASUREMENTS.items():
        print(f"Fetching {meta['label']} (measurement {meta['id']}), last {hours}h...")
        raw = fetch_measurement(meta["id"], hours=hours)
        print(f"  {len(raw):,} raw real probe readings")
        buckets = aggregate_to_buckets(raw)
        print(f"  aggregated to {len(buckets)} ten-minute buckets")

        out_path = DATA_DIR / f"ripe_{key}.json"
        with open(out_path, "w") as f:
            json.dump({"meta": meta, "buckets": buckets}, f, indent=2)
        manifest[key] = {**meta, "bucket_count": len(buckets), "raw_sample_count": len(raw)}

    with open(DATA_DIR / "manifest.json", "w") as f:
        json.dump({"fetched_at": int(time.time()), "measurements": manifest}, f, indent=2)
    print(f"\nSaved real-world measurement data to {DATA_DIR}")


if __name__ == "__main__":
    fetch_all()
