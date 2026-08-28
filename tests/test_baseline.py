"""Offline contract tests for the fair single-agent baseline infrastructure."""

from pathlib import Path

import pytest

from resolveops.agents.baseline.artifacts import ArtifactStore, RunManifest
from resolveops.agents.baseline.config import (
    DEFAULT_MODEL,
    DEFAULT_REASONING_EFFORT,
    BaselineConfig,
)
from resolveops.agents.baseline.factory import create_baseline_agent
from resolveops.agents.baseline.prompt import BASELINE_PROMPT_ID
from resolveops.agents.baseline.records import BaselineTrajectory, RecordedToolCall, RuntimeRecord
from resolveops.agents.baseline.runner import select_case
from resolveops.agents.baseline.tools import BASELINE_TOOLS, DIRECT_TOOL_WRAPPERS
from resolveops.domain import ToolResult
from resolveops.evaluation.candidate import with_authoritative_case_id
from resolveops.evaluation.models import CandidateDraft, EvaluationCase
from resolveops.evaluation.models import CandidateOutput, EvidenceReference, RuntimeMetrics


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


def test_baseline_runtime_has_no_truth_or_scoring_imports() -> None:
    root = Path("resolveops/agents/baseline")
    source = "\n".join(path.read_text(encoding="utf-8") for path in root.glob("*.py"))
    for forbidden in ("hidden_truth", "benchmark_truth", "score_benchmark", "load_hidden_truths"):
        assert forbidden not in source


def test_candidate_metadata_helper_has_no_hidden_truth_dependency() -> None:
    source = Path("resolveops/evaluation/candidate.py").read_text(encoding="utf-8")
    for forbidden in ("hidden_truth", "benchmark_truth", "load_hidden_truths"):
        assert forbidden not in source
