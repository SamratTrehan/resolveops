"""Offline coverage for the session-only Judge Challenge."""

import hashlib
import inspect
import re
import tomllib
from pathlib import Path
from types import SimpleNamespace

import pytest

from resolveops.agents.resolveops.schemas import EvidenceBundleDraft, ObservedFact, VerificationDecision
from resolveops.app import judge_challenge
from resolveops.app.demo_data import HISTORICAL_REPLAY, reset_approval_for_mode
from resolveops.app.judge_challenge import (
    ChallengeAllowanceUsed,
    ChallengeExecutionError,
    ChallengeUnavailable,
    FRESH_RUN_COUNT_KEY,
    FRESH_RESULT_KEY,
    MAX_FRESH_RUNS_PER_SESSION,
    challenge_case,
    challenge_templates,
    configured_server_key,
    execute_challenge,
    fresh_allowance_available,
    fresh_runs_remaining,
    resolution_packet_export,
    run_challenge_once,
    stage_mapping,
)
from resolveops.evaluation.models import CandidateDraft, EvidenceReference
from resolveops.tools.simulator import default_environment


ROOT = Path(__file__).resolve().parents[1]
FROZEN = (
    ROOT / "evaluation/results/baseline/baseline-official-004",
    ROOT / "evaluation/results/resolveops/resolveops-phase4-002",
    ROOT / "evaluation/results/resolveops/resolveops-phase5a-001",
    ROOT / "resolveops/evaluation/data/benchmark_truth.json",
    ROOT / "evaluation/reports/final_comparison.json",
)


def _hashes(paths: tuple[Path, ...] = FROZEN) -> dict[str, str]:
    files = [item for path in paths for item in ([path] if path.is_file() else sorted(path.rglob("*"))) if item.is_file()]
    return {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in files}


def _fake_sdk_run(agent: object, user_input: str, **kwargs: object) -> object:
    context = kwargs["context"]
    customer_id = re.search(r"CUS-\d{3}", user_input).group()
    tool_result = default_environment().get_account_status(customer_id)
    reference = EvidenceReference(tool_name="get_account_status", source_id=customer_id)
    if agent.name == "ResolveOps Investigator":
        context.record("get_account_status", {"customer_id": customer_id}, tool_result)
        output = EvidenceBundleDraft(
            ticket_summary="Synthetic connectivity ticket.",
            observed_facts=[ObservedFact(statement=tool_result.summary, evidence_references=[reference])],
            evidence_references=[reference],
            investigation_summary="Synthetic account evidence collected.",
        )
    elif agent.name == "ResolveOps Verifier":
        output = VerificationDecision(approved=True, feedback="Evidence and resolution are consistent.")
    else:
        approval_required = customer_id == "CUS-003"
        output = CandidateDraft(
            root_cause_id="pending_gateway_provisioning" if approval_required else "regional_outage",
            confidence=0.82,
            recommended_action_id="guide_gateway_activation" if approval_required else "communicate_outage_status",
            escalate=False,
            evidence_references=[reference],
            customer_response="Synthetic customer response.",
            internal_notes="Synthetic internal notes.",
        )
    return SimpleNamespace(final_output=output, context_wrapper=None)


def test_server_key_resolution_and_missing_key_do_not_consume_allowance() -> None:
    example = tomllib.loads((ROOT / ".streamlit/secrets.toml.example").read_text(encoding="utf-8"))
    assert example == {"OPENAI_API_KEY": ""}
    assert ".streamlit/secrets.toml" in (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert configured_server_key({"OPENAI_API_KEY": "server-secret"}, {"OPENAI_API_KEY": "local-secret"}) == "server-secret"
    assert configured_server_key({}, {"OPENAI_API_KEY": "local-secret"}) == "local-secret"
    assert configured_server_key({}, {}) is None
    state: dict[str, object] = {}
    assert MAX_FRESH_RUNS_PER_SESSION == 3 and fresh_runs_remaining(state) == 3
    with pytest.raises(ChallengeUnavailable):
        run_challenge_once(state, "CASE-001", "Synthetic symptom.", None, _fake_sdk_run)
    assert fresh_runs_remaining(state) == 3 and FRESH_RUN_COUNT_KEY not in state


def test_fresh_runs_consume_three_session_allowances_and_preserve_runtime_evidence() -> None:
    before = _hashes()
    state: dict[str, object] = {}
    result = run_challenge_once(state, "CASE-001", "Judge paraphrased synthetic symptom.", "test-secret", _fake_sdk_run)
    assert result.case.ticket_text == "Judge paraphrased synthetic symptom."
    assert result.case.customer_id == "CUS-002" and result.case.primary_device_id == "DEV-003"
    assert result.model == "gpt-5.6-terra" and result.reasoning_effort == "medium"
    assert not result.benchmark_scored and state[FRESH_RUN_COUNT_KEY] == 1 and fresh_runs_remaining(state) == 2
    assert FRESH_RESULT_KEY in state and "test-secret" not in repr(state)
    reset_approval_for_mode(state, HISTORICAL_REPLAY)
    assert state[FRESH_RUN_COUNT_KEY] == 1
    assert [stage.prompt_id for stage in result.stages] == ["investigator-v1", "resolver-v1", "verifier-v1"]
    assert result.stages[0].tool_calls[0].tool_name == "get_account_status"
    assert "CUS-002" in result.stages[0].tool_calls[0].result.source_ids
    assert stage_mapping(result)["investigator-v1"]["output"]["observed_facts"]
    export = resolution_packet_export(result)
    assert export["benchmark_scored"] is False and export["run_id"] == result.run_id
    assert export["label"] == "Fresh demonstration run — not benchmark-scored."
    assert _hashes() == before
    run_challenge_once(state, "CASE-001", "Another symptom.", "test-secret", _fake_sdk_run)
    assert state[FRESH_RUN_COUNT_KEY] == 2 and fresh_runs_remaining(state) == 1
    run_challenge_once(state, "CASE-001", "Third symptom.", "test-secret", _fake_sdk_run)
    assert state[FRESH_RUN_COUNT_KEY] == 3 and fresh_runs_remaining(state) == 0
    with pytest.raises(ChallengeAllowanceUsed):
        run_challenge_once(state, "CASE-001", "Fourth symptom.", "test-secret", _fake_sdk_run)


def test_failed_model_attempt_consumes_allowance_without_exposing_secret(caplog: pytest.LogCaptureFixture) -> None:
    secret = "test-secret-must-not-leak"

    def fail_model(*args: object, **kwargs: object) -> object:
        raise TimeoutError(secret)

    state: dict[str, object] = {}
    with pytest.raises(ChallengeExecutionError, match="did not complete"):
        run_challenge_once(state, "CASE-001", "Synthetic symptom.", secret, fail_model)
    assert state[FRESH_RUN_COUNT_KEY] == 1 and fresh_runs_remaining(state) == 2 and fresh_allowance_available(state)
    assert secret not in repr(state) and secret not in caplog.text


def test_inputs_are_public_world_bound_and_ticket_edit_does_not_mutate_state() -> None:
    templates = challenge_templates()
    environment = default_environment()
    assert len(templates) == 15
    for case in templates:
        assert case.customer_id in environment.customers
        if case.primary_device_id:
            device = environment.devices[case.primary_device_id]
            assert environment.accounts[device.account_id].customer_id == case.customer_id
    world = ROOT / "data/support_world.json"
    before = hashlib.sha256(world.read_bytes()).hexdigest()
    changed = challenge_case("CASE-001", "A rewritten synthetic symptom.")
    original = next(case for case in templates if case.case_id == "CASE-001")
    assert changed.ticket_text != original.ticket_text
    assert (changed.customer_id, changed.primary_device_id) == (original.customer_id, original.primary_device_id)
    assert hashlib.sha256(world.read_bytes()).hexdigest() == before
    with pytest.raises(ValueError):
        challenge_case("CASE-999", "Synthetic symptom.")


def test_hidden_truth_is_absent_and_fresh_ids_are_unique(monkeypatch: pytest.MonkeyPatch) -> None:
    source = inspect.getsource(judge_challenge).lower()
    assert "benchmark_truth" not in source and "hidden_truth" not in source
    read_text = Path.read_text

    def reject_truth(path: Path, *args: object, **kwargs: object) -> str:
        if path.name == "benchmark_truth.json":
            raise AssertionError("Judge Challenge attempted to read hidden truth.")
        return read_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", reject_truth)
    case = challenge_case("CASE-001", "Synthetic symptom.")
    first = execute_challenge(case, "test-secret", _fake_sdk_run)
    second = execute_challenge(case, "test-secret", _fake_sdk_run)
    assert first.run_id != second.run_id
    assert first.run_id.startswith("judge-") and first.started_at.tzinfo is not None


def test_approval_required_fresh_resolution_remains_pending() -> None:
    result = execute_challenge(challenge_case("CASE-002", "Replacement gateway will not activate."), "test-secret", _fake_sdk_run)
    assert result.candidate.recommended_action_id == "guide_gateway_activation"
    assert result.safety_gate.approval_required
    assert result.safety_gate.approval_status.value == "pending"
    assert result.safety_gate.execution_status == "blocked_pending_approval"
