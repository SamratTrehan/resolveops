"""Read-only, safe data loaders for the Streamlit judge demo."""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
FORBIDDEN = ("acceptable_root", "acceptable_action", "forbidden_claim", "evaluator_note", "hidden_truth")


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
    labels = ("Baseline", "Investigator", "Verifier")
    return [{"stage": label, "vrsr": run["vrsr_percent"], "evidence": run["evidence_coverage"]} for label, run in zip(labels, report["runs"])]


def comparison_report() -> dict[str, object] | None:
    path = ROOT / "evaluation/reports/final_comparison.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


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
