import hashlib
from pathlib import Path

from resolveops.app import demo_data
from resolveops.agents.resolveops.safety import ApprovalStatus, HumanApproval, safety_gate
from resolveops.app.demo_data import (
    HISTORICAL_REPLAY,
    IMPROVEMENT_CHART_HEIGHT,
    JUDGE_SIMULATION,
    JUDGE_CHALLENGE,
    chart_data,
    comparison_rows,
    comparison_report,
    display_label,
    evidence_coverage_data,
    evidence_cards,
    judge_demo_case,
    mode_comparison,
    mode_metadata,
    observable_case,
    playback,
    playback_cases,
    reset_transient_approval,
    reset_approval_for_mode,
    revision_diff,
    simulation_scenarios,
    workflow_stages,
    workflow_steps,
)


def test_demo_loaders_are_read_only_and_hide_evaluator_fields() -> None:
    assert comparison_report()["runs"][0]["run_id"] == "baseline-official-004"
    assert "CASE-003" in playback_cases()
    stages = playback("resolveops-phase5a-001", "CASE-003")
    assert "investigator-v1" in stages and "verifier-v1" in stages
    assert display_label("INSUFFICIENT_EVIDENCE") == "Insufficient Evidence"
    assert judge_demo_case() == "CASE-005"
    assert revision_diff(stages)
    assert [name for name, _ in workflow_stages(stages)][:3] == ["investigator-v1", "resolver-v1", "verifier-v1"]
    assert comparison_rows(stages)
    assert chart_data(comparison_report())[0]["stage"] == "Baseline"
    assert evidence_coverage_data(comparison_report()) == [
        {"stage": "Baseline", "evidence": 73.33333333333333},
        {"stage": "Investigator + Resolver", "evidence": 93.33333333333333},
        {"stage": "Final ResolveOps", "evidence": 100.0},
    ]
    assert IMPROVEMENT_CHART_HEIGHT == 180
    assert evidence_cards(stages["investigator-v1"]["output"])
    for row in comparison_rows(stages):
        assert isinstance(row["before"], str) and isinstance(row["after"], str) and row["changed"] in {"✓", "—"}


def test_no_key_judge_and_replay_modes_use_recorded_observable_artifacts_only() -> None:
    assert [row["mode"] for row in mode_comparison()] == ["Interactive Judge Simulation", "Judge Challenge", "Historical Replay"]
    assert [row["api_key"] for row in mode_comparison()] == ["No", "Server", "No"]
    assert JUDGE_SIMULATION.endswith("No API key required")
    assert JUDGE_CHALLENGE == "Judge Challenge — Fresh Inference"
    assert HISTORICAL_REPLAY.endswith("No API key required")
    assert [(item["label"], item["badge"]) for item in mode_metadata()] == [
        ("Interactive Judge Simulation", "NO KEY"),
        ("Judge Challenge", "FRESH"),
        ("Historical Replay", "RECORDED"),
    ]
    steps = workflow_steps("Verifier")
    assert [step["label"] for step in steps] == ["Ticket", "Investigator", "Resolver", "Verifier", "Conditional Revision", "Safety Gate", "Resolution"]
    assert [step["label"] for step in steps if step["active"]] == ["Verifier"]
    assert all(label.isascii() for label in [step["label"] for step in steps])

    scenarios = simulation_scenarios()
    assert [scenario["label"] for scenario in scenarios] == ["Service outage", "Wi-Fi / local connectivity", "Camera / device issue", "Insufficient evidence / escalation", "Provisioning / approval-required"]
    for scenario in scenarios:
        case = scenario["case"]
        assert case["case_id"] in playback_cases()
        assert observable_case(case["case_id"])["ticket_text"] == case["ticket_text"]
        assert not any(field in case for field in demo_data.FORBIDDEN)


def test_simulation_is_read_only_and_approval_is_session_local() -> None:
    path = Path("trajectories/resolveops/resolveops-phase5a-001/CASE-002-investigator-v1.json")
    before = hashlib.sha256(path.read_bytes()).hexdigest()
    stages = playback("resolveops-phase5a-001", "CASE-002")
    assert stages["resolver-v1"]["output"]["recommended_action_id"] == "guide_gateway_activation"
    assert hashlib.sha256(path.read_bytes()).hexdigest() == before

    state = {"approval_context": "simulation:CASE-002", "approval_decision": "approve"}
    reset_transient_approval(state, "replay:CASE-003")
    assert state == {"approval_context": "replay:CASE-003"}
    reset_transient_approval(state, "replay:CASE-003")
    assert state == {"approval_context": "replay:CASE-003"}
    assert "run_case" not in Path(demo_data.__file__).read_text(encoding="utf-8")


def test_approval_state_survives_same_scenario_rerun_and_resets_on_case_or_mode_change() -> None:
    state: dict[str, object] = {}
    reset_approval_for_mode(state, JUDGE_SIMULATION)
    reset_transient_approval(state, "simulation:CASE-002")
    state["approval_decision"] = "approve"
    reset_approval_for_mode(state, JUDGE_SIMULATION)
    reset_transient_approval(state, "simulation:CASE-002")
    assert state["approval_decision"] == "approve"
    reset_transient_approval(state, "simulation:CASE-005")
    assert "approval_decision" not in state
    state["approval_decision"] = "reject"
    assert safety_gate("guide_gateway_activation", HumanApproval(state["approval_decision"])).approval_status is ApprovalStatus.REJECTED
    reset_approval_for_mode(state, HISTORICAL_REPLAY)
    assert state == {"approval_mode": HISTORICAL_REPLAY}
