import hashlib
from pathlib import Path

from resolveops.app import demo_data
from resolveops.app.demo_data import (
    BASELINE_BATTLE_RUN,
    RESOLVEOPS_BATTLE_RUN,
    case_battle,
    case_battle_case_ids,
    case_battle_divergences,
    default_case_battle_case,
    safe_score_projection,
)


ROOT = Path(__file__).resolve().parents[1]


def test_case_battle_uses_only_the_frozen_fair_comparison_runs() -> None:
    assert (BASELINE_BATTLE_RUN, RESOLVEOPS_BATTLE_RUN) == ("baseline-official-004", "resolveops-phase5a-001")
    assert case_battle_case_ids() == ["CASE-001", "CASE-002", "CASE-004", "CASE-005", "CASE-006", "CASE-007", "CASE-008", "CASE-009", "CASE-010", "CASE-011", "CASE-012", "CASE-013", "CASE-014", "CASE-015"]
    assert default_case_battle_case() == "CASE-006"


def test_case_battle_is_safe_read_only_and_artifact_grounded() -> None:
    trajectory = ROOT / "trajectories/resolveops/resolveops-phase5a-001/CASE-006-verifier-v1.json"
    before = hashlib.sha256(trajectory.read_bytes()).hexdigest()
    battle = case_battle("CASE-006")
    assert hashlib.sha256(trajectory.read_bytes()).hexdigest() == before
    assert battle["case"]["case_id"] == "CASE-006"
    assert battle["baseline"]["score"] == {
        "case_id": "CASE-006", "passed": False, "diagnosis_correct": True, "action_correct": True,
        "escalation_correct": True, "evidence_coverage": False, "execution_failure": False,
    }
    assert battle["resolveops"]["score"]["passed"] is True
    assert battle["resolveops"]["verifier"]["revision_occurred"] is True
    assert "ResolveOps cited 4 additional evidence references." in case_battle_divergences(battle)
    assert {row["status"] for row in battle["evidence"]} <= {"Shared", "Baseline only", "ResolveOps only"}


def test_case_battle_score_projection_never_exposes_evaluator_metadata_or_model_execution() -> None:
    projection = safe_score_projection({"case_id": "CASE-X", "passed": True, "acceptable_root_causes": ["secret"], "forbidden_claim_violations": ["secret"]})
    assert projection == {"case_id": "CASE-X", "passed": True, "diagnosis_correct": None, "action_correct": None, "escalation_correct": None, "evidence_coverage": None, "execution_failure": None}
    source = Path(demo_data.__file__).read_text(encoding="utf-8")
    assert "benchmark_truth" not in source
    assert "run_case" not in source
