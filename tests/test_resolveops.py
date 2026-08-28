"""Offline Phase 4 Investigator-to-Resolver contracts."""

from types import SimpleNamespace

import pytest

from agents.exceptions import ModelBehaviorError

from resolveops.agents.baseline.config import BaselineConfig
from resolveops.agents.baseline.runner import select_case
from resolveops.agents.resolveops.factory import create_investigator, create_resolver
from resolveops.agents.resolveops.evidence import canonical_tool_name, normalize_evidence_bundle, with_authoritative_evidence_case_id
from resolveops.agents.resolveops.prompts import INVESTIGATOR_INSTRUCTIONS, RESOLVER_INSTRUCTIONS
from resolveops.agents.resolveops.runner import run_case
from resolveops.agents.resolveops.runner import _metrics
from resolveops.agents.resolveops.records import AgentAttempt
from resolveops.evaluation.models import RuntimeMetrics
from resolveops.agents.resolveops.schemas import EvidenceBundle, EvidenceBundleDraft, Hypothesis, ObservedFact
from resolveops.evaluation.models import CandidateDraft, EvidenceReference
from resolveops.evaluation.score_resolveops_results import score_saved_run
from resolveops.agents.resolveops.artifacts import ResolveOpsArtifactStore, ResolveOpsManifest
from resolveops.agents.baseline.records import RuntimeRecord
from resolveops.evaluation.models import CandidateOutput, ExecutionFailure


def _bundle() -> EvidenceBundleDraft:
    return EvidenceBundleDraft(ticket_summary="Internet unavailable.", hypotheses=[Hypothesis(label="outage", rationale="Needs evidence.")], investigation_summary="No tool evidence yet.")


def _draft() -> CandidateDraft:
    return CandidateDraft(root_cause_id="regional_outage", confidence=0.8, recommended_action_id="communicate_outage_status", escalate=False, customer_response="Synthetic response.", internal_notes="Synthetic notes.")


def test_investigator_and_resolver_tool_and_prompt_boundaries() -> None:
    config = BaselineConfig()
    assert {tool.name for tool in create_investigator(config).tools} == {"get_account_status", "get_device_status", "run_connectivity_diagnostics", "check_service_outages", "get_ticket_history", "search_knowledge_base"}
    assert create_resolver(config).tools == []
    for prompt in (INVESTIGATOR_INSTRUCTIONS, RESOLVER_INSTRUCTIONS):
        for forbidden in ("CASE-", "acceptable_", "forbidden_claim", "required_tool", "required_source"):
            assert forbidden not in prompt
    assert "regional_outage" in RESOLVER_INSTRUCTIONS


def test_evidence_bundle_rejects_malformed_case_and_handoff_preserves_case_id() -> None:
    with pytest.raises(ValueError):
        EvidenceBundle(case_id="bad", ticket_summary="x", investigation_summary="x")
    calls: list[str] = []

    def fake_run(agent: object, user_input: str, **kwargs: object) -> object:
        calls.append(agent.name)
        return SimpleNamespace(final_output=_bundle() if agent.name == "ResolveOps Investigator" else _draft(), context_wrapper=None)

    candidate, investigator, resolver = run_case(select_case("CASE-001"), BaselineConfig(), "phase4-test", fake_run)
    assert candidate and candidate.case_id == "CASE-001"
    assert calls == ["ResolveOps Investigator", "ResolveOps Resolver"]
    assert investigator.prompt_id == "investigator-v1"
    assert resolver and resolver.prompt_id == "resolver-v1"
    assert investigator.runtime_metrics.latency_ms is not None and resolver.runtime_metrics.latency_ms is not None
    assert '"case_id": "CASE-001"' in resolver.input_summary


def test_investigator_malformed_json_retries_once_and_prevents_resolver() -> None:
    calls: list[str] = []

    def fake_run(agent: object, user_input: str, **kwargs: object) -> object:
        calls.append(agent.name)
        raise ModelBehaviorError("Invalid JSON when parsing model output")

    candidate, investigator, resolver = run_case(select_case("CASE-001"), BaselineConfig(), "phase4-retry", fake_run)
    assert candidate is None and resolver is None
    assert calls == ["ResolveOps Investigator", "ResolveOps Investigator"]
    assert len(investigator.attempts) == 2 and investigator.runtime_metrics.retries == 1


def test_bundle_structure_supports_facts_with_real_reference_shape() -> None:
    bundle = EvidenceBundle(case_id="CASE-001", ticket_summary="Ticket.", observed_facts=[ObservedFact(statement="Outage observed.", evidence_references=[EvidenceReference(tool_name="check_service_outages", source_id="OUT-001")])], investigation_summary="Outage evidence collected.")
    assert bundle.observed_facts[0].evidence_references[0].source_id == "OUT-001"


def test_authoritative_evidence_case_id_is_not_model_controlled() -> None:
    draft = EvidenceBundleDraft(ticket_summary="Ticket.", investigation_summary="No evidence yet.")
    bundle = with_authoritative_evidence_case_id(select_case("CASE-001"), draft)
    assert bundle.case_id == "CASE-001"
    with pytest.raises(ValueError):
        EvidenceBundleDraft.model_validate({"case_id": "CASE-002", "ticket_summary": "Ticket.", "investigation_summary": "No evidence yet."})


def test_agent_token_aggregation_is_complete_or_null() -> None:
    known = [AgentAttempt(attempt_number=1, status="completed", runtime_metrics=RuntimeMetrics(latency_ms=2, tool_call_count=3), usage={"input_tokens": 100, "output_tokens": 200, "reasoning_tokens": 4587, "total_tokens": 4887})]
    assert _metrics(known).token_usage == 4887
    retry = known + [AgentAttempt(attempt_number=2, status="completed", runtime_metrics=RuntimeMetrics(latency_ms=3, tool_call_count=4), usage={"input_tokens": 10, "output_tokens": 20, "reasoning_tokens": 30, "total_tokens": 60})]
    metrics = _metrics(retry)
    assert (metrics.token_usage, metrics.retries, metrics.tool_call_count, metrics.latency_ms) == (4947, 1, 0, 5)
    missing = retry + [AgentAttempt(attempt_number=3, status="failed", runtime_metrics=RuntimeMetrics(latency_ms=1, tool_call_count=0))]
    assert _metrics(missing).token_usage is None


def test_sdk_qualified_evidence_references_are_canonicalized_narrowly() -> None:
    tools = ("get_account_status", "get_device_status", "run_connectivity_diagnostics", "check_service_outages", "get_ticket_history", "search_knowledge_base")
    assert [canonical_tool_name(name) for name in tools] == list(tools)
    assert [canonical_tool_name(f"functions.{name}") for name in tools] == list(tools)
    assert canonical_tool_name("fake.get_account_status") == "fake.get_account_status"
    bundle = EvidenceBundle(case_id="CASE-001", ticket_summary="x", evidence_references=[EvidenceReference(tool_name="functions.get_account_status", source_id="ACC-002")], observed_facts=[ObservedFact(statement="Account observed.", evidence_references=[EvidenceReference(tool_name="functions.get_device_status", source_id="DEV-003")])], investigation_summary="x")
    normalized = normalize_evidence_bundle(bundle)
    assert normalized.evidence_references[0].tool_name == "get_account_status"
    assert normalized.observed_facts[0].evidence_references[0].tool_name == "get_device_status"


def test_resolveops_scoring_wrapper_scores_completed_full_artifacts(tmp_path) -> None:
    store = ResolveOpsArtifactStore("score-wrapper", root=tmp_path)
    cases = [select_case(f"CASE-{number:03}") for number in range(1, 16)]
    store.prepare()
    candidates = {case.case_id: CandidateOutput(case_id=case.case_id, root_cause_id="regional_outage", confidence=0, recommended_action_id="communicate_outage_status", escalate=False, customer_response="x", internal_notes="x") for case in cases[:-1]}
    failure = ExecutionFailure(case_id=cases[-1].case_id, error_type="ModelBehaviorError", error_message="Invalid JSON", infrastructure_retries=1)
    store.write_results(candidates, {case.case_id: RuntimeRecord(model="test", reasoning_effort="medium", metrics=RuntimeMetrics()) for case in cases}, {failure.case_id: failure}, ResolveOpsManifest(run_id="score-wrapper", run_kind="official", model="test", reasoning_effort="medium", investigator_prompt_id="investigator-v1", resolver_prompt_id="resolver-v1", case_ids=[case.case_id for case in cases], successful_candidate_count=14, execution_failure_count=1))
    score_saved_run("score-wrapper", root=tmp_path)
    assert (store.result_dir / "score_summary.json").exists()
    assert (store.result_dir / "case_scores.json").exists()


def test_resolveops_scoring_wrapper_rejects_failure_marker(tmp_path) -> None:
    store = ResolveOpsArtifactStore("incomplete-wrapper", root=tmp_path)
    store.prepare()
    ResolveOpsArtifactStore._write(store.result_dir / "failure.json", {"status": "failed"})
    with pytest.raises(RuntimeError, match="incomplete"):
        score_saved_run("incomplete-wrapper", root=tmp_path)
