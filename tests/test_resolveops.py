"""Offline Phase 4 Investigator-to-Resolver contracts."""

from types import SimpleNamespace

import pytest

from agents.exceptions import ModelBehaviorError

from resolveops.agents.baseline.config import BaselineConfig
from resolveops.agents.baseline.runner import select_case
from resolveops.agents.resolveops.factory import create_investigator, create_resolver
from resolveops.agents.resolveops.evidence import with_authoritative_evidence_case_id
from resolveops.agents.resolveops.prompts import INVESTIGATOR_INSTRUCTIONS, RESOLVER_INSTRUCTIONS
from resolveops.agents.resolveops.runner import run_case
from resolveops.agents.resolveops.schemas import EvidenceBundle, EvidenceBundleDraft, Hypothesis, ObservedFact
from resolveops.evaluation.models import CandidateDraft, EvidenceReference


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
