"""Read-only, safe data loaders for the Streamlit judge demo."""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
FORBIDDEN = ("acceptable_root", "acceptable_action", "forbidden_claim", "evaluator_note", "hidden_truth")


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
