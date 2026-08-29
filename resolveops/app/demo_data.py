"""Read-only, safe data loaders for the Streamlit judge demo."""

import json
from pathlib import Path
from typing import MutableMapping


ROOT = Path(__file__).resolve().parents[2]
FORBIDDEN = ("acceptable_root", "acceptable_action", "forbidden_claim", "evaluator_note", "hidden_truth")
JUDGE_SIMULATION = "Interactive Judge Simulation — No API key required"
JUDGE_CHALLENGE = "Judge Challenge — Fresh Inference"
HISTORICAL_REPLAY = "Historical Replay — No API key required"
MODE_METADATA = (
    {"id": JUDGE_SIMULATION, "label": "Interactive Judge Simulation", "badge": "NO KEY", "summary": "Full guided experience", "api_key": "No", "inference": "No"},
    {"id": JUDGE_CHALLENGE, "label": "Judge Challenge", "badge": "FRESH", "summary": "New model inference on one synthetic ticket", "api_key": "Server", "inference": "Yes"},
    {"id": HISTORICAL_REPLAY, "label": "Historical Replay", "badge": "RECORDED", "summary": "Inspect official recorded runs", "api_key": "No", "inference": "No"},
)
WORKFLOW_LABELS = ("Ticket", "Investigator", "Resolver", "Verifier", "Conditional Revision", "Safety Gate", "Resolution")
IMPROVEMENT_STAGE_LABELS = ("Baseline", "Investigator + Resolver", "Final ResolveOps")
IMPROVEMENT_CHART_HEIGHT = 180
BASELINE_BATTLE_RUN = "baseline-official-004"
RESOLVEOPS_BATTLE_RUN = "resolveops-phase5a-001"
FEATURED_BATTLE_CASE = "CASE-006"
SAFE_SCORE_FIELDS = ("case_id", "passed", "diagnosis_correct", "action_correct", "escalation_correct", "evidence_coverage", "execution_failure")
SIMULATION_SCENARIOS = (
    ("Service outage", "CASE-001"),
    ("Wi-Fi / local connectivity", "CASE-005"),
    ("Camera / device issue", "CASE-008"),
    ("Insufficient evidence / escalation", "CASE-011"),
    ("Provisioning / approval-required", "CASE-002"),
)


def display_label(value: str | None) -> str:
    return (value or "Not available").replace("_", " ").title()


def judge_demo_case() -> str:
    return "CASE-005" if "CASE-005" in playback_cases() else playback_cases()[0]


def revision_diff(stages: dict[str, dict[str, object]]) -> dict[str, tuple[object, object]]:
    before = stages.get("resolver-v1", {}).get("output", {})
    after = stages.get("resolver-revision-v1", {}).get("output", before)
    return {key: (before.get(key), after.get(key)) for key in ("root_cause_id", "recommended_action_id", "escalate", "confidence", "evidence_references", "customer_response") if before.get(key) != after.get(key)}


def evidence_groups(bundle: dict[str, object]) -> dict[str, list[dict[str, object]]]:
    groups = {"Account": [], "Device": [], "Diagnostics": [], "Outage": [], "Ticket History": [], "Knowledge Base": []}
    names = {"get_account_status": "Account", "get_device_status": "Device", "run_connectivity_diagnostics": "Diagnostics", "check_service_outages": "Outage", "get_ticket_history": "Ticket History", "search_knowledge_base": "Knowledge Base"}
    for item in bundle.get("evidence_references", []):
        groups[names.get(item.get("tool_name"), "Device")].append(item)
    return groups


def workflow_stages(stages: dict[str, dict[str, object]]) -> list[tuple[str, dict[str, object]]]:
    order = ("investigator-v1", "resolver-v1", "verifier-v1", "resolver-revision-v1")
    return [(name, stages[name]) for name in order if name in stages]


def evidence_cards(bundle: dict[str, object]) -> dict[str, list[dict[str, str]]]:
    groups = evidence_groups(bundle)
    facts = bundle.get("observed_facts", [])
    statements = {ref.get("source_id"): fact.get("statement", "Observed evidence.") for fact in facts for ref in fact.get("evidence_references", [])}
    return {group: [{"source_id": item.get("source_id", ""), "tool_name": item.get("tool_name", ""), "statement": statements.get(item.get("source_id"), "Observed evidence.")} for item in refs] for group, refs in groups.items()}


def comparison_rows(stages: dict[str, dict[str, object]]) -> list[dict[str, object]]:
    before = stages.get("resolver-v1", {}).get("output", {}); after = stages.get("resolver-revision-v1", {}).get("output", before)
    keys = ("root_cause_id", "recommended_action_id", "escalate", "confidence")
    def cell(value: object) -> str:
        if isinstance(value, bool): return "True" if value else "False"
        if isinstance(value, float): return f"{value:.2f}"
        return str(value)
    rows = [{"label": display_label(key), "before": cell(before.get(key)), "after": cell(after.get(key)), "changed": "✓" if before.get(key) != after.get(key) else "—"} for key in keys]
    count_before, count_after = len(before.get("evidence_references", [])), len(after.get("evidence_references", []))
    rows.append({"label": "Evidence Count", "before": cell(count_before), "after": cell(count_after), "changed": "✓" if count_before != count_after else "—"})
    return rows


def chart_data(report: dict[str, object]) -> list[dict[str, object]]:
    return [{"stage": label, "vrsr": run["vrsr_percent"], "evidence": run["evidence_coverage"]} for label, run in zip(IMPROVEMENT_STAGE_LABELS, report["runs"])]


def evidence_coverage_data(report: dict[str, object]) -> list[dict[str, object]]:
    return [{"stage": item["stage"], "evidence": item["evidence"]} for item in chart_data(report)]


def comparison_report() -> dict[str, object] | None:
    path = ROOT / "evaluation/reports/final_comparison.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def mode_comparison() -> list[dict[str, str]]:
    return [{"mode": item["label"], "api_key": item["api_key"], "inference": item["inference"]} for item in MODE_METADATA]


def mode_metadata() -> tuple[dict[str, str], ...]:
    return MODE_METADATA


def workflow_steps(active: str = "Ticket") -> list[dict[str, object]]:
    return [{"label": label, "active": label == active} for label in WORKFLOW_LABELS]


def observable_case(case_id: str) -> dict[str, object]:
    cases = json.loads((ROOT / "data/cases/benchmark_cases.json").read_text(encoding="utf-8"))
    return next(case for case in cases if case["case_id"] == case_id)


def simulation_scenarios() -> list[dict[str, object]]:
    recorded = set(playback_cases())
    return [
        {"label": label, "case": observable_case(case_id)}
        for label, case_id in SIMULATION_SCENARIOS
        if case_id in recorded
    ]


def reset_transient_approval(state: MutableMapping[str, object], context: str) -> None:
    if state.get("approval_context") != context:
        state["approval_context"] = context
        state.pop("approval_decision", None)


def reset_approval_for_mode(state: MutableMapping[str, object], mode: str) -> None:
    if state.get("approval_mode") != mode:
        state["approval_mode"] = mode
        state.pop("approval_context", None)
        state.pop("approval_decision", None)


def _result_artifact(namespace: str, run_id: str, name: str) -> object:
    return json.loads((ROOT / "evaluation/results" / namespace / run_id / name).read_text(encoding="utf-8"))


def safe_score_projection(record: dict[str, object]) -> dict[str, object]:
    return {field: record.get(field) for field in SAFE_SCORE_FIELDS}


def _battle_artifacts() -> tuple[dict[str, object], dict[str, object], dict[str, dict[str, object]], dict[str, dict[str, object]]]:
    baseline_candidates = _result_artifact("baseline", BASELINE_BATTLE_RUN, "candidates.json")
    resolveops_candidates = _result_artifact("resolveops", RESOLVEOPS_BATTLE_RUN, "candidates.json")
    baseline_scores = _result_artifact("baseline", BASELINE_BATTLE_RUN, "case_scores.json")
    resolveops_scores = _result_artifact("resolveops", RESOLVEOPS_BATTLE_RUN, "case_scores.json")
    return baseline_candidates, resolveops_candidates, {item["case_id"]: safe_score_projection(item) for item in baseline_scores}, {item["case_id"]: safe_score_projection(item) for item in resolveops_scores}


def case_battle_case_ids() -> list[str]:
    baseline, resolveops, _, _ = _battle_artifacts()
    return sorted(set(baseline).intersection(resolveops))


def default_case_battle_case() -> str:
    cases = case_battle_case_ids()
    return FEATURED_BATTLE_CASE if FEATURED_BATTLE_CASE in cases else cases[0]


def _evidence_rows(baseline: list[dict[str, str]], resolveops: list[dict[str, str]]) -> list[dict[str, str]]:
    groups = {"get_account_status": "Account", "get_device_status": "Device", "run_connectivity_diagnostics": "Diagnostics", "check_service_outages": "Outage", "get_ticket_history": "Ticket History", "search_knowledge_base": "Knowledge Base"}
    baseline_keys = {(item["tool_name"], item["source_id"]) for item in baseline}
    resolveops_keys = {(item["tool_name"], item["source_id"]) for item in resolveops}
    rows = []
    for tool_name, source_id in sorted(baseline_keys | resolveops_keys):
        status = "Shared" if (tool_name, source_id) in baseline_keys & resolveops_keys else "Baseline only" if (tool_name, source_id) in baseline_keys else "ResolveOps only"
        rows.append({"group": groups.get(tool_name, "Other"), "source_id": source_id, "tool_name": tool_name, "status": status})
    return rows


def _verifier_projection(case_id: str) -> dict[str, object]:
    stages = playback(RESOLVEOPS_BATTLE_RUN, case_id)
    verifier = stages.get("verifier-v1", {}).get("output", {})
    changes = revision_diff(stages)
    return {
        "approved": verifier.get("approved"),
        "issue_categories": [item.get("category") for item in verifier.get("issues", [])],
        "revision_occurred": "resolver-revision-v1" in stages,
        "changed_fields": [display_label(key) for key in changes],
        "before_evidence_count": len((stages.get("resolver-v1", {}).get("output", {})).get("evidence_references", [])),
        "after_evidence_count": len((stages.get("resolver-revision-v1", {}).get("output", stages.get("resolver-v1", {}).get("output", {}))).get("evidence_references", [])),
        "before_confidence": (stages.get("resolver-v1", {}).get("output", {})).get("confidence"),
        "after_confidence": (stages.get("resolver-revision-v1", {}).get("output", stages.get("resolver-v1", {}).get("output", {}))).get("confidence"),
    }


def case_battle(case_id: str) -> dict[str, object]:
    baseline, resolveops, baseline_scores, resolveops_scores = _battle_artifacts()
    if case_id not in set(baseline).intersection(resolveops):
        raise ValueError(f"Case is not comparable: {case_id}")
    baseline_runtime = _result_artifact("baseline", BASELINE_BATTLE_RUN, "runtime.json")[case_id]["metrics"]
    resolveops_runtime = _result_artifact("resolveops", RESOLVEOPS_BATTLE_RUN, "runtime.json")[case_id]["metrics"]
    baseline_candidate, resolveops_candidate = baseline[case_id], resolveops[case_id]
    return {
        "case": observable_case(case_id),
        "baseline": {"candidate": baseline_candidate, "runtime": baseline_runtime, "score": baseline_scores[case_id], "architecture": "Ticket → General Agent → Resolution"},
        "resolveops": {"candidate": resolveops_candidate, "runtime": resolveops_runtime, "score": resolveops_scores[case_id], "architecture": "Ticket → Investigator → Resolver → Verifier → optional Revision → Resolution", "investigator_evidence_count": len((playback(RESOLVEOPS_BATTLE_RUN, case_id).get("investigator-v1", {}).get("output", {})).get("evidence_references", [])), "verifier": _verifier_projection(case_id)},
        "evidence": _evidence_rows(baseline_candidate["evidence_references"], resolveops_candidate["evidence_references"]),
    }


def case_battle_divergences(battle: dict[str, object]) -> list[str]:
    baseline, resolveops = battle["baseline"], battle["resolveops"]
    baseline_refs = len(baseline["candidate"]["evidence_references"])
    resolveops_refs = len(resolveops["candidate"]["evidence_references"])
    messages = []
    if resolveops_refs > baseline_refs:
        messages.append(f"ResolveOps cited {resolveops_refs - baseline_refs} additional evidence references.")
    if not baseline["score"]["evidence_coverage"] and resolveops["score"]["evidence_coverage"]:
        messages.append("Required evidence-reference coverage did not pass for the baseline and passed for ResolveOps.")
    verifier = resolveops["verifier"]
    if verifier["revision_occurred"]:
        messages.append("The Verifier requested one bounded Resolver revision.")
    else:
        messages.append("ResolveOps added a separate Verifier without a revision.")
    if baseline["candidate"]["root_cause_id"] != resolveops["candidate"]["root_cause_id"]:
        messages.append("The architectures produced different diagnosis labels.")
    if baseline["candidate"]["recommended_action_id"] != resolveops["candidate"]["recommended_action_id"]:
        messages.append("The architectures produced different recommended actions.")
    return messages


def playback_cases(run_id: str = "resolveops-phase5a-001") -> list[str]:
    path = ROOT / "trajectories/resolveops" / run_id
    return sorted({item.name.split("-investigator-v1.json")[0] for item in path.glob("*-investigator-v1.json")}) if path.exists() else []


def playback(run_id: str, case_id: str) -> dict[str, dict[str, object]]:
    root = ROOT / "trajectories/resolveops" / run_id
    found = {}
    for path in root.glob(f"{case_id}-*.json"):
        value = json.loads(path.read_text(encoding="utf-8"))
        serialized = json.dumps(value).lower()
        if any(token in serialized for token in FORBIDDEN):
            raise ValueError("Playback artifact contains evaluator-only content.")
        found[path.stem.removeprefix(f"{case_id}-")] = value
    return found
