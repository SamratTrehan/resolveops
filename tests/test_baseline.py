"""Offline contract tests for the fair single-agent baseline infrastructure."""

import json
from pathlib import Path

import pytest

from agents.exceptions import ModelBehaviorError

from resolveops.agents.baseline.artifacts import ArtifactStore, FailedRunRecord, RunManifest
from resolveops.agents.baseline.config import (
    DEFAULT_MODEL,
    DEFAULT_REASONING_EFFORT,
    BaselineConfig,
)
from resolveops.agents.baseline.factory import create_baseline_agent
from resolveops.agents.baseline.prompt import (
    BASELINE_INSTRUCTIONS,
    BASELINE_PROMPT_ID,
    BASELINE_V2_INSTRUCTIONS,
    BASELINE_V2_PROMPT_ID,
)
from resolveops.agents.baseline.records import BaselineAttempt, BaselineTrajectory, RecordedToolCall, RuntimeRecord
from resolveops.agents.baseline.runner import CaseRunError, run_case, run_cases, select_case
from resolveops.agents.baseline.tools import BASELINE_TOOLS, DIRECT_TOOL_WRAPPERS
from resolveops.domain import ToolResult
from resolveops.domain.support_ontology import ActionId, RootCauseId
from resolveops.evaluation.candidate import with_authoritative_case_id
from resolveops.evaluation.models import CandidateDraft, EvaluationCase
from resolveops.evaluation.models import CandidateOutput, EvidenceReference, ExecutionFailure, RuntimeMetrics
from resolveops.evaluation.score_baseline_results import score_saved_run


def _candidate(case_id: str = "CASE-001") -> CandidateOutput:
    return CandidateOutput(
        case_id=case_id,
        root_cause_id="regional_outage",
        confidence=0.8,
        recommended_action_id="communicate_outage_status",
        escalate=False,
        evidence_references=[EvidenceReference(tool_name="check_service_outages", source_id="OUT-001")],
        customer_response="Synthetic response.",
        internal_notes="Synthetic note.",
    )


def test_all_six_simulator_capabilities_are_exposed() -> None:
    assert set(DIRECT_TOOL_WRAPPERS) == {
        "get_account_status",
        "get_device_status",
        "run_connectivity_diagnostics",
        "check_service_outages",
        "get_ticket_history",
        "search_knowledge_base",
    }
    assert {tool.name for tool in BASELINE_TOOLS} == set(DIRECT_TOOL_WRAPPERS)


def test_wrappers_preserve_structured_success_and_evidence_ids() -> None:
    result = DIRECT_TOOL_WRAPPERS["check_service_outages"]("CUS-002")
    assert result.success
    assert result.source_ids == ["CUS-002", "OUT-001"]
    assert result.evidence[1].entity_id == "OUT-001"


def test_wrappers_preserve_simulator_errors() -> None:
    result = DIRECT_TOOL_WRAPPERS["get_device_status"]("DEV-999")
    assert not result.success
    assert result.error == "Device not found: DEV-999"


def test_baseline_agent_uses_existing_candidate_output_contract() -> None:
    agent = create_baseline_agent(BaselineConfig(model="configured-model", reasoning_effort="medium"))
    assert agent.output_type is CandidateDraft
    assert agent.model == "configured-model"
    assert agent.model_settings.reasoning.effort == "medium"
    assert agent.instructions == BASELINE_V2_INSTRUCTIONS


def test_public_ontology_ids_are_exact_and_candidate_schema_enforces_them() -> None:
    assert [item.value for item in RootCauseId] == [
        "regional_outage", "pending_gateway_provisioning", "camera_reconnect_needed",
        "dns_resolution_failure", "local_wifi_configuration", "account_standing_question",
        "INSUFFICIENT_EVIDENCE",
    ]
    assert [item.value for item in ActionId] == [
        "communicate_outage_status", "guide_gateway_activation", "guide_camera_reconnect",
        "guide_dns_recovery", "guide_wifi_reconnect", "review_account_notice",
        "escalate_for_more_evidence",
    ]
    for root_cause_id in RootCauseId:
        for recommended_action_id in ActionId:
            draft = CandidateDraft(
                root_cause_id=root_cause_id, confidence=0.5, recommended_action_id=recommended_action_id,
                escalate=False, customer_response="Synthetic response.", internal_notes="Synthetic note.",
            )
            assert draft.model_dump(mode="json")["root_cause_id"] == root_cause_id.value
            assert draft.model_dump(mode="json")["recommended_action_id"] == recommended_action_id.value


def test_candidate_schema_rejects_arbitrary_root_and_action_ids() -> None:
    with pytest.raises(ValueError):
        CandidateDraft(
            root_cause_id="invented_root", confidence=0.5, recommended_action_id="guide_dns_recovery",
            escalate=False, customer_response="Synthetic response.", internal_notes="Synthetic note.",
        )
    with pytest.raises(ValueError):
        CandidateDraft(
            root_cause_id="regional_outage", confidence=0.5, recommended_action_id="invented_action",
            escalate=False, customer_response="Synthetic response.", internal_notes="Synthetic note.",
        )


def test_public_ontology_and_baseline_v2_expose_contract_without_case_truth() -> None:
    ontology = Path("resolveops/domain/support_ontology.py").read_text(encoding="utf-8")
    for forbidden in ("CASE-", "acceptable_", "forbidden_claim", "required_tool", "required_source"):
        assert forbidden not in ontology
    assert BASELINE_INSTRUCTIONS == """You are the single general-purpose ResolveOps baseline support agent.
You are resolving a synthetic technical-support ticket. Use the available read-only
diagnostic and knowledge-base tools when they help establish a reliable answer.

Return the required structured CandidateOutput. Ground root_cause_id,
recommended_action_id, escalate, and asserted_claim_ids in the ticket and actual
tool results. Evidence references must name only tools you actually called and
source IDs returned by those tools. Do not invent unavailable facts or source IDs.
When the available evidence cannot support a reliable resolution, use
INSUFFICIENT_EVIDENCE, recommend an escalation action, and set escalate to true.
Keep customer_response clear and internal_notes concise.
"""
    assert BASELINE_V2_PROMPT_ID == "baseline-v2"
    assert BASELINE_V2_INSTRUCTIONS.startswith(BASELINE_INSTRUCTIONS)
    for item in (*RootCauseId, *ActionId):
        assert item.value in BASELINE_V2_INSTRUCTIONS
    for forbidden in ("CASE-", "acceptable_", "forbidden_claim", "required_tool", "required_source"):
        assert forbidden not in BASELINE_V2_INSTRUCTIONS


def test_model_configuration_uses_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RESOLVEOPS_MODEL", "test-model")
    monkeypatch.setenv("RESOLVEOPS_REASONING_EFFORT", "high")
    config = BaselineConfig.from_environment()
    assert (config.model, config.reasoning_effort) == ("test-model", "high")


def test_benchmark_configuration_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("RESOLVEOPS_MODEL", raising=False)
    monkeypatch.delenv("RESOLVEOPS_REASONING_EFFORT", raising=False)
    config = BaselineConfig.from_environment()
    assert (config.model, config.reasoning_effort) == (DEFAULT_MODEL, DEFAULT_REASONING_EFFORT)


def test_reasoning_effort_validation_rejects_unsupported_value() -> None:
    with pytest.raises(ValueError, match="RESOLVEOPS_REASONING_EFFORT"):
        BaselineConfig(model="test-model", reasoning_effort="ultra")


def test_authoritative_case_id_keeps_a_correct_model_id() -> None:
    case = EvaluationCase(case_id="CASE-001", ticket_text="Synthetic ticket.", customer_id="CUS-001")
    candidate = _candidate("CASE-001")
    final_candidate = with_authoritative_case_id(case, CandidateDraft.model_validate(candidate.model_dump()))
    assert final_candidate == candidate


def test_authoritative_case_id_replaces_an_incorrect_model_id_only() -> None:
    case = EvaluationCase(case_id="CASE-001", ticket_text="Synthetic ticket.", customer_id="CUS-001")
    model_candidate = _candidate("CASE-002")
    final_candidate = with_authoritative_case_id(
        case,
        CandidateDraft.model_validate(model_candidate.model_dump()),
    )
    assert final_candidate.case_id == "CASE-001"
    assert final_candidate.model_dump(exclude={"case_id"}) == model_candidate.model_dump(exclude={"case_id"})


def test_draft_schema_ignores_malformed_model_case_metadata() -> None:
    case = EvaluationCase(case_id="CASE-001", ticket_text="Synthetic ticket.", customer_id="CUS-001")
    payload = _candidate("CASE-002").model_dump()
    payload["case_id"] = "not-a-case-id"
    final_candidate = with_authoritative_case_id(case, CandidateDraft.model_validate(payload))
    assert final_candidate.case_id == "CASE-001"


def test_trajectory_serialization_preserves_tool_evidence() -> None:
    tool_result = ToolResult(tool_name="get_device_status", success=True, summary="ok", source_ids=["DEV-001"])
    trajectory = BaselineTrajectory(
        run_id="smoke-001",
        case_id="CASE-001",
        model="test-model",
        reasoning_effort="medium",
        agent_name="ResolveOps Baseline",
        prompt_id=BASELINE_PROMPT_ID,
        status="completed",
        tool_calls=[RecordedToolCall(tool_name="get_device_status", arguments={"device_id": "DEV-001"}, result=tool_result)],
        final_output=with_authoritative_case_id(
            EvaluationCase(case_id="CASE-001", ticket_text="Synthetic ticket.", customer_id="CUS-001"),
            CandidateDraft.model_validate(_candidate("CASE-002").model_dump()),
        ),
        runtime_metrics=RuntimeMetrics(latency_ms=12, retries=0, tool_call_count=1),
    )
    restored = BaselineTrajectory.model_validate_json(trajectory.model_dump_json())
    assert restored.tool_calls[0].result.source_ids == ["DEV-001"]
    assert restored.case_id == restored.final_output.case_id == "CASE-001"


def test_artifact_paths_are_deterministic_and_non_overwriting(tmp_path: Path) -> None:
    store = ArtifactStore("smoke-001", root=tmp_path)
    case = EvaluationCase(case_id="CASE-001", ticket_text="Synthetic ticket.", customer_id="CUS-001")
    final_candidate = with_authoritative_case_id(
        case,
        CandidateDraft.model_validate(_candidate("CASE-002").model_dump()),
    )
    assert store.result_dir == tmp_path / "evaluation" / "results" / "baseline" / "smoke-001"
    assert store.trajectory_dir == tmp_path / "trajectories" / "baseline" / "smoke-001"
    store.prepare()
    store.write_results(
        {"CASE-001": final_candidate},
        {"CASE-001": RuntimeRecord(model="test-model", reasoning_effort="medium", metrics=RuntimeMetrics(latency_ms=12, retries=0, tool_call_count=1))},
        {},
        RunManifest(
            run_id="smoke-001",
            run_kind="development",
            model="test-model",
            reasoning_effort="medium",
            agent_name="ResolveOps Baseline",
            prompt_id=BASELINE_PROMPT_ID,
            case_ids=["CASE-001"],
        ),
    )
    assert (store.result_dir / "candidates.json").exists()
    candidates = (store.result_dir / "candidates.json").read_text(encoding="utf-8")
    assert '"case_id": "CASE-001"' in candidates
    assert '"case_id": "CASE-002"' not in candidates
    runtime = (store.result_dir / "runtime.json").read_text(encoding="utf-8")
    assert '"reasoning_effort": "medium"' in runtime
    manifest = (store.result_dir / "manifest.json").read_text(encoding="utf-8")
    assert '"reasoning_effort": "medium"' in manifest
    with pytest.raises(FileExistsError):
        ArtifactStore("smoke-001", root=tmp_path).prepare()
    assert (store.result_dir / "candidates.json").read_text(encoding="utf-8") == candidates


def test_partial_collision_does_not_create_or_delete_artifacts(tmp_path: Path) -> None:
    store = ArtifactStore("smoke-002", root=tmp_path)
    store.result_dir.mkdir(parents=True)
    sentinel = store.result_dir / "existing.json"
    sentinel.write_text('{"preserve": true}\n', encoding="utf-8")

    with pytest.raises(FileExistsError):
        store.prepare()

    assert sentinel.read_text(encoding="utf-8") == '{"preserve": true}\n'
    assert not store.trajectory_dir.exists()


def test_invalid_benchmark_case_id_fails_clearly() -> None:
    with pytest.raises(ValueError, match="Unknown benchmark case ID"):
        select_case("CASE-999")


class _Result:
    def __init__(self, final_output: CandidateDraft) -> None:
        self.final_output = final_output
        self.context_wrapper = None


def _draft() -> CandidateDraft:
    return CandidateDraft.model_validate(_candidate().model_dump())


def test_invalid_json_retries_once_with_identical_execution_inputs() -> None:
    case = select_case("CASE-001")
    calls: list[tuple[object, str, object, int]] = []

    def fake_run(agent: object, user_input: str, **kwargs: object) -> _Result:
        calls.append((agent, user_input, kwargs["context"], kwargs["max_turns"]))
        if len(calls) == 1:
            raise ModelBehaviorError("Invalid JSON when parsing model output")
        return _Result(_draft())

    candidate, trajectory = run_case(case, BaselineConfig(), "retry-test", run_sync=fake_run)
    assert candidate.case_id == case.case_id
    assert trajectory.status == "completed"
    assert trajectory.infrastructure_retries == trajectory.runtime_metrics.retries == 1
    assert [item.status for item in trajectory.attempts] == ["failed", "completed"]
    assert [item.error for item in trajectory.attempts] == ["ModelBehaviorError: Invalid JSON when parsing model output", None]
    assert trajectory.prompt_id == BASELINE_V2_PROMPT_ID
    assert all(item.prompt_id == BASELINE_V2_PROMPT_ID for item in trajectory.attempts)
    assert calls[0][1:] == calls[1][1:]
    assert calls[0][0].model == calls[1][0].model == "gpt-5.6-terra"
    assert calls[0][0].model_settings.reasoning.effort == calls[1][0].model_settings.reasoning.effort == "medium"
    assert calls[0][0].instructions == calls[1][0].instructions


def test_two_invalid_json_failures_stop_after_one_retry() -> None:
    attempts = 0

    def fake_run(*args: object, **kwargs: object) -> _Result:
        nonlocal attempts
        attempts += 1
        raise ModelBehaviorError("Invalid JSON when parsing model output")

    with pytest.raises(CaseRunError) as error:
        run_case(select_case("CASE-001"), BaselineConfig(), "retry-stop", run_sync=fake_run)
    assert attempts == 2
    assert error.value.trajectory.infrastructure_retries == 1
    assert len(error.value.trajectory.attempts) == 2


def test_other_model_behavior_errors_are_not_retried() -> None:
    attempts = 0

    def fake_run(*args: object, **kwargs: object) -> _Result:
        nonlocal attempts
        attempts += 1
        raise ModelBehaviorError("Model called an unavailable tool")

    with pytest.raises(CaseRunError):
        run_case(select_case("CASE-001"), BaselineConfig(), "no-tool-retry", run_sync=fake_run)
    assert attempts == 1


def test_valid_candidate_is_not_retried_even_if_it_would_score_poorly() -> None:
    calls = 0

    def fake_run(*args: object, **kwargs: object) -> _Result:
        nonlocal calls
        calls += 1
        draft = _draft()
        draft.root_cause_id = RootCauseId.INSUFFICIENT_EVIDENCE
        return _Result(draft)

    _, trajectory = run_case(select_case("CASE-001"), BaselineConfig(), "no-retry", run_sync=fake_run)
    assert calls == 1
    assert trajectory.infrastructure_retries == 0


def test_failure_artifact_preserves_partial_run_and_blocks_scoring(tmp_path: Path) -> None:
    store = ArtifactStore("failed-run", root=tmp_path)
    store.prepare()
    store.write_failure(
        {},
        {},
        FailedRunRecord(
            run_id="failed-run", run_kind="official", model="test-model", reasoning_effort="medium",
            agent_name="ResolveOps Baseline", prompt_id=BASELINE_PROMPT_ID,
            requested_case_ids=["CASE-001"], completed_case_ids=[], failed_case_id="CASE-001",
            error_type="ModelBehaviorError", error_message="Invalid JSON when parsing model output",
        ),
    )
    with pytest.raises(RuntimeError, match="incomplete"):
        score_saved_run("failed-run", root=tmp_path)
    assert (store.result_dir / "failure.json").exists()
    assert '"status": "failed"' in (store.result_dir / "failure.json").read_text(encoding="utf-8")


def test_runner_writes_failed_run_record_without_overwriting_partial_results(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    store = ArtifactStore("failed-runner", root=tmp_path)
    first_case, failed_case = [select_case(case_id) for case_id in ("CASE-001", "CASE-002")]

    def trajectory(case: EvaluationCase, status: str) -> BaselineTrajectory:
        return BaselineTrajectory(
            run_id="failed-runner", case_id=case.case_id, model="test-model", reasoning_effort="medium",
            agent_name="ResolveOps Baseline", prompt_id=BASELINE_PROMPT_ID, status=status,
            runtime_metrics=RuntimeMetrics(latency_ms=1, retries=0, tool_call_count=0),
        )

    def fake_run_case(case: EvaluationCase, *args: object) -> tuple[CandidateOutput, BaselineTrajectory]:
        if case.case_id == first_case.case_id:
            return _candidate(case.case_id), trajectory(case, "completed")
        raise CaseRunError(trajectory(case, "failed"))

    monkeypatch.setattr("resolveops.agents.baseline.runner.ArtifactStore", lambda run_id: store)
    monkeypatch.setattr("resolveops.agents.baseline.runner.run_case", fake_run_case)
    with pytest.raises(CaseRunError):
        run_cases([first_case, failed_case], BaselineConfig(model="test-model", reasoning_effort="medium"), "failed-runner")

    failure = (store.result_dir / "failure.json").read_text(encoding="utf-8")
    candidates = (store.result_dir / "candidates.json").read_text(encoding="utf-8")
    assert '"completed_case_ids": [\n    "CASE-001"\n  ]' in failure
    assert '"failed_case_id": "CASE-002"' in failure
    assert '"CASE-001"' in candidates
    with pytest.raises(FileExistsError):
        store.write_failure({}, {}, FailedRunRecord(
            run_id="failed-runner", run_kind="development", model="test-model", reasoning_effort="medium",
            agent_name="ResolveOps Baseline", prompt_id=BASELINE_PROMPT_ID,
            requested_case_ids=[], completed_case_ids=[], failed_case_id="CASE-002",
            error_type="CaseRunError", error_message="already present",
        ))
    assert (store.result_dir / "candidates.json").read_text(encoding="utf-8") == candidates


def test_all_case_runner_continues_after_execution_failure(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    store = ArtifactStore("continue-run", root=tmp_path)
    cases = [select_case(case_id) for case_id in ("CASE-001", "CASE-002", "CASE-003")]
    attempted: list[str] = []

    def trajectory(case: EvaluationCase, status: str) -> BaselineTrajectory:
        return BaselineTrajectory(
            run_id="continue-run", case_id=case.case_id, model="test-model", reasoning_effort="medium",
            agent_name="ResolveOps Baseline", prompt_id=BASELINE_PROMPT_ID, status=status,
            infrastructure_retries=1 if status == "failed" else 0,
            runtime_metrics=RuntimeMetrics(latency_ms=1, retries=1 if status == "failed" else 0, tool_call_count=0),
        )

    def fake_run_case(case: EvaluationCase, *args: object) -> tuple[CandidateOutput, BaselineTrajectory]:
        attempted.append(case.case_id)
        if case.case_id == "CASE-002":
            raise CaseRunError(trajectory(case, "failed")) from ModelBehaviorError("Invalid JSON when parsing model output")
        return _candidate(case.case_id), trajectory(case, "completed")

    monkeypatch.setattr("resolveops.agents.baseline.runner.ArtifactStore", lambda run_id: store)
    monkeypatch.setattr("resolveops.agents.baseline.runner.run_case", fake_run_case)
    run_cases(cases, BaselineConfig(model="test-model", reasoning_effort="medium"), "continue-run", continue_on_execution_failure=True)

    assert attempted == ["CASE-001", "CASE-002", "CASE-003"]
    assert (store.trajectory_dir / "CASE-002.json").exists()
    failures = (store.result_dir / "execution_failures.json").read_text(encoding="utf-8")
    assert '"CASE-002"' in failures and '"INSUFFICIENT_EVIDENCE"' not in failures
    manifest = (store.result_dir / "manifest.json").read_text(encoding="utf-8")
    assert '"status": "completed"' in manifest
    assert '"execution_failure_count": 1' in manifest
    assert '"prompt_id": "baseline-v2"' in manifest
    assert not (store.result_dir / "failure.json").exists()


def test_completed_all_case_artifacts_with_execution_failure_are_scoreable(tmp_path: Path) -> None:
    store = ArtifactStore("scoreable-run", root=tmp_path)
    cases = [select_case(f"CASE-{number:03}") for number in range(1, 16)]
    failed_case = cases[-1]
    store.prepare()
    store.write_results(
        {case.case_id: _candidate(case.case_id) for case in cases[:-1]},
        {
            case.case_id: RuntimeRecord(
                model="test-model", reasoning_effort="medium",
                metrics=RuntimeMetrics(latency_ms=1, retries=0, tool_call_count=0),
            )
            for case in cases
        },
        {
            failed_case.case_id: ExecutionFailure(
                case_id=failed_case.case_id,
                error_type="ModelBehaviorError",
                error_message="Invalid JSON when parsing model output",
                infrastructure_retries=1,
            )
        },
        RunManifest(
            run_id="scoreable-run", run_kind="official", model="test-model", reasoning_effort="medium",
            agent_name="ResolveOps Baseline", prompt_id=BASELINE_PROMPT_ID,
            case_ids=[case.case_id for case in cases], successful_candidate_count=14, execution_failure_count=1,
        ),
    )
    score_saved_run("scoreable-run", root=tmp_path)
    scores = json.loads((store.result_dir / "case_scores.json").read_text(encoding="utf-8"))
    failed_score = next(score for score in scores if score["case_id"] == failed_case.case_id)
    assert failed_score["execution_failure"] and not failed_score["passed"]


def test_baseline_runtime_has_no_truth_or_scoring_imports() -> None:
    root = Path("resolveops/agents/baseline")
    source = "\n".join(path.read_text(encoding="utf-8") for path in root.glob("*.py"))
    for forbidden in ("hidden_truth", "benchmark_truth", "score_benchmark", "load_hidden_truths"):
        assert forbidden not in source


def test_candidate_metadata_helper_has_no_hidden_truth_dependency() -> None:
    source = Path("resolveops/evaluation/candidate.py").read_text(encoding="utf-8")
    for forbidden in ("hidden_truth", "benchmark_truth", "load_hidden_truths"):
        assert forbidden not in source
