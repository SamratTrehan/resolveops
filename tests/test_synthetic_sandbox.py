"""Offline coverage for the session-local consequential-action sandbox."""

from datetime import datetime, timezone
import hashlib
import inspect
from pathlib import Path

from resolveops.agents.resolveops.safety import HumanApproval
from resolveops.app.synthetic_sandbox import (
    SANDBOX_STATE_KEY,
    SyntheticActionRequest,
    execute_synthetic_action,
    read_sandbox_state,
)
from resolveops.domain.support_ontology import ActionId


ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 8, 29, tzinfo=timezone.utc)
FROZEN = (
    ROOT / "data/support_world.json",
    ROOT / "evaluation/results/baseline/baseline-official-004",
    ROOT / "evaluation/results/resolveops/resolveops-phase4-002",
    ROOT / "evaluation/results/resolveops/resolveops-phase5a-001",
    ROOT / "resolveops/evaluation/data/benchmark_truth.json",
    ROOT / "evaluation/reports/final_comparison.json",
)


def _hashes() -> dict[str, str]:
    files = [file for path in FROZEN for file in ([path] if path.is_file() else sorted(path.rglob("*"))) if file.is_file()]
    return {str(file): hashlib.sha256(file.read_bytes()).hexdigest() for file in files}


def _request(
    *,
    context: str = "simulation:CASE-002",
    decision: HumanApproval | None = None,
    action: ActionId = ActionId.GUIDE_GATEWAY_ACTIVATION,
    customer_id: str = "CUS-003",
    device_id: str | None = "DEV-004",
) -> SyntheticActionRequest:
    return SyntheticActionRequest(
        context=context,
        run_or_case_id="CASE-002",
        customer_id=customer_id,
        primary_device_id=device_id,
        action_id=action,
        human_decision=decision,
    )


def test_sandbox_starts_from_canonical_world_without_mutating_it() -> None:
    world = ROOT / "data/support_world.json"
    before = hashlib.sha256(world.read_bytes()).hexdigest()
    state: dict[str, object] = {}
    current = read_sandbox_state(state, "simulation:CASE-002", "CUS-003", "DEV-004")
    assert current.provisioning_status == "awaiting_gateway_activation"
    assert current.service_activation == "pending"
    assert hashlib.sha256(world.read_bytes()).hexdigest() == before


def test_pending_and_rejection_are_blocked_and_read_back_pending() -> None:
    for decision, expected in ((None, "blocked_pending_approval"), (HumanApproval.REJECT, "blocked_rejected")):
        state: dict[str, object] = {}
        result = execute_synthetic_action(state, _request(decision=decision), now=NOW)
        assert not result.executed and result.execution_status == expected
        assert result.before_state == result.after_state
        assert read_sandbox_state(state, "simulation:CASE-002", "CUS-003", "DEV-004").provisioning_status == "awaiting_gateway_activation"
        assert SANDBOX_STATE_KEY not in state


def test_approval_commits_once_and_read_back_confirms_active() -> None:
    state: dict[str, object] = {}
    approved = execute_synthetic_action(state, _request(decision=HumanApproval.APPROVE), now=NOW)
    assert approved.executed and approved.execution_status == "completed"
    assert approved.before_state.provisioning_status == "awaiting_gateway_activation"
    assert approved.after_state.provisioning_status == "complete"
    assert read_sandbox_state(state, "simulation:CASE-002", "CUS-003", "DEV-004").provisioning_status == "complete"

    repeated = execute_synthetic_action(state, _request(decision=HumanApproval.APPROVE), now=NOW)
    assert not repeated.executed and repeated.execution_status == "already_active"
    assert repeated.blocked_reason == "Already active — no additional state change required."


def test_invalid_action_target_and_malformed_state_fail_closed() -> None:
    state: dict[str, object] = {}
    invalid_action = execute_synthetic_action(
        state, _request(action=ActionId.GUIDE_WIFI_RECONNECT, decision=HumanApproval.APPROVE), now=NOW
    )
    assert invalid_action.execution_status == "blocked_validation" and SANDBOX_STATE_KEY not in state

    invalid_target = execute_synthetic_action(
        state, _request(customer_id="CUS-999", decision=HumanApproval.APPROVE), now=NOW
    )
    assert invalid_target.execution_status == "blocked_validation" and SANDBOX_STATE_KEY not in state

    malformed: dict[str, object] = {SANDBOX_STATE_KEY: "not-a-mapping"}
    result = execute_synthetic_action(malformed, _request(decision=HumanApproval.APPROVE), now=NOW)
    assert result.execution_status == "blocked_validation" and malformed[SANDBOX_STATE_KEY] == "not-a-mapping"


def test_sandbox_is_context_and_target_scoped() -> None:
    state: dict[str, object] = {}
    execute_synthetic_action(state, _request(context="simulation:CASE-002", decision=HumanApproval.APPROVE), now=NOW)
    assert read_sandbox_state(state, "simulation:CASE-002", "CUS-003", "DEV-004").provisioning_status == "complete"
    assert read_sandbox_state(state, "fresh:judge-1", "CUS-003", "DEV-004").provisioning_status == "awaiting_gateway_activation"
    assert read_sandbox_state(state, "simulation:CASE-002", "CUS-001", "DEV-001").provisioning_status == "complete"

    independent_session: dict[str, object] = {}
    assert read_sandbox_state(independent_session, "simulation:CASE-002", "CUS-003", "DEV-004").provisioning_status == "awaiting_gateway_activation"


def test_sandbox_has_no_hidden_truth_or_trajectory_writes() -> None:
    source = inspect.getsource(__import__("resolveops.app.synthetic_sandbox", fromlist=["*"])).lower()
    assert "benchmark_truth" not in source and "hidden_truth" not in source
    before = _hashes()
    execute_synthetic_action({}, _request(decision=HumanApproval.APPROVE), now=NOW)
    assert _hashes() == before
