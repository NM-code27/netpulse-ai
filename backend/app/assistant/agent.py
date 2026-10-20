"""
Turns an evidence bundle (alert + root-cause ranking + business impact +
current metric snapshot) into a natural-language explanation an on-call
engineer can act on. The LLM is grounded with the actual evidence in the
prompt and told not to invent numbers; if the LLM is unreachable (e.g. Ollama
isn't running), a deterministic template built from the same evidence is
returned instead, so the assistant panel never goes blank.
"""
from app.assistant.llm_client import LLMUnavailableError, complete

RECOMMENDED_STEPS = {
    "wan_link": [
        "Check the WAN circuit's provider-side status page / ticket queue for the affected site.",
        "Run a continuous traceroute from the site router toward the hub to localize where latency is introduced.",
        "Check for a concurrent large transfer or backup job saturating the link.",
        "If packet loss persists, open a carrier ticket with the loss/latency timeseries attached.",
    ],
    "device": [
        "Check CPU, memory and interface error counters on the device via SNMP/CLI.",
        "Check for a recent config change or firmware update around the time the anomaly started.",
        "Look for interface flaps or duplex mismatches in the device log.",
        "If CPU is pegged, check for a routing loop or an unexpected traffic spike.",
    ],
    "dns": [
        "Check the core DNS resolver's query latency and cache hit rate.",
        "Verify upstream/forwarder resolvers are reachable from the resolver host.",
        "Check resolver CPU/memory and recent zone or config changes.",
        "If multiple sites are affected simultaneously, treat this as the primary suspect over any single site's link.",
    ],
    "app_tier": [
        "Check the application tier's request queue depth and backend DB latency.",
        "Check for a recent deployment or config change on the app tier.",
        "Check app-tier CPU/memory and autoscaling status.",
        "If multiple sites are affected simultaneously, treat this as the primary suspect over any single site's link.",
    ],
}


def _evidence_text(evidence: dict) -> str:
    rc = evidence.get("root_cause", [])
    lines = [
        f"Site: {evidence.get('site_name')} ({evidence.get('site_id')})",
        f"Triggering metric: {evidence.get('metric_name')} = {evidence.get('current_value')} "
        f"(risk score {evidence.get('risk_score')}/100, anomaly score {evidence.get('anomaly_score')}/100, "
        f"lead time {evidence.get('lead_time_minutes')} min)",
        "Root-cause ranking (rule+ML correlation across topology):",
    ]
    for i, c in enumerate(rc[:3], start=1):
        lines.append(f"  {i}. {c['label']} -- confidence {c['confidence']}% (entity: {c['entity_id']})")
    bi = evidence.get("business_impact", {})
    lines.append(
        f"Business impact: {bi.get('users_affected', 0)} users across "
        f"{len(bi.get('sites_affected', []))} site(s), apps: {', '.join(bi.get('apps_affected', [])) or 'n/a'}, "
        f"severity tier: {bi.get('severity_tier')}"
    )
    return "\n".join(lines)


def template_explanation(evidence: dict) -> str:
    rc = evidence.get("root_cause", [])
    top = rc[0] if rc else None
    category = top["category"] if top else "unknown"
    steps = RECOMMENDED_STEPS.get(category, ["Investigate the affected entity directly."])
    bi = evidence.get("business_impact", {})

    lines = [
        f"**Likely cause: {top['label'] if top else 'undetermined'}** "
        f"(confidence {top['confidence'] if top else 0}%).",
        "",
        f"Evidence: {evidence.get('metric_name')} on {evidence.get('site_name')} is at "
        f"{evidence.get('current_value')}, giving a risk score of {evidence.get('risk_score')}/100 "
        f"with an estimated {evidence.get('lead_time_minutes')} minute(s) of advance warning before "
        f"a hard breach, and an anomaly score of {evidence.get('anomaly_score')}/100 against this metric's "
        f"learned normal range.",
        "",
    ]
    if rc and len(rc) > 1:
        lines.append(
            "Other candidates considered: " +
            "; ".join(f"{c['label']} ({c['confidence']}%)" for c in rc[1:3])
        )
        lines.append("")
    lines.append(
        f"Estimated business impact: {bi.get('users_affected', 0)} users across "
        f"{len(bi.get('sites_affected', []))} site(s) depending on "
        f"{', '.join(bi.get('apps_affected', [])) or 'the affected service'}."
    )
    lines.append("")
    lines.append("Recommended next steps:")
    for s in steps:
        lines.append(f"  - {s}")
    return "\n".join(lines)


SYSTEM_PROMPT = (
    "You are a network operations assistant. You are given evidence already "
    "computed by a correlation engine (anomaly scores, a forecasted outage-risk "
    "score, a lead-time estimate, a ranked root-cause candidate list, and a "
    "business-impact estimate). Explain, in under 150 words, what is most likely "
    "wrong, cite the specific numbers given, and list concrete next diagnostic "
    "steps. Do not invent metrics or numbers that were not given to you."
)


def explain(evidence: dict) -> dict:
    rc = evidence.get("root_cause", [])
    category = rc[0]["category"] if rc else "device"
    grounding_steps = RECOMMENDED_STEPS.get(category, [])
    prompt = (
        f"{_evidence_text(evidence)}\n\n"
        f"Candidate diagnostic steps for this category: {grounding_steps}\n\n"
        "Write the explanation and next steps now."
    )
    try:
        text = complete(prompt, system=SYSTEM_PROMPT)
        if text:
            return {"text": text, "source": f"llm:{_provider_label()}"}
    except LLMUnavailableError:
        pass
    return {"text": template_explanation(evidence), "source": "template"}


def _provider_label() -> str:
    from app.config import settings
    return settings.llm_provider
