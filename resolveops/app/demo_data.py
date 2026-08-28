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
