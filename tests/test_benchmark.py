"""Integrity and scoring tests for the fixed, offline Phase 2 benchmark."""

import json
import re
from pathlib import Path

from resolveops.evaluation import (
    CandidateOutput,
    EvidenceReference,
    RuntimeMetrics,
    load_cases,
    score_benchmark,
    score_case,
    validate_benchmark_integrity,
)
from resolveops.evaluation.hidden_truth import load_hidden_truths
from resolveops.tools import default_environment


def _perfect_candidate(case_id: str) -> CandidateOutput:
    truth = {item.case_id: item for item in load_hidden_truths()}[case_id]
    references = [EvidenceReference(tool_name=tool) for tool in truth.required_tools]
    references.extend(EvidenceReference(tool_name="evidence_source", source_id=source_id) for source_id in truth.required_source_ids)
    return CandidateOutput(
        case_id=case_id,
        root_cause_id=truth.acceptable_root_causes[0],
        confidence=0.8,
        recommended_action_id=truth.acceptable_actions[0],
        escalate=truth.must_escalate,
        evidence_references=references,
        customer_response="Synthetic response.",
        internal_notes="Synthetic evidence-backed note.",
    )


def test_exactly_fifteen_cases_load() -> None:
    assert len(load_cases()) == 15


def test_every_case_has_truth_and_no_truth_is_orphaned() -> None:
    cases = load_cases()
    truths = load_hidden_truths()
    validate_benchmark_integrity(cases, truths, default_environment())
    assert {case.case_id for case in cases} == {truth.case_id for truth in truths}


def test_cases_reference_existing_customer_and_device_ids() -> None:
    environment = default_environment()
    for case in load_cases():
        assert case.customer_id in environment.customers
        assert case.primary_device_id in environment.devices


def test_hidden_truth_source_ids_exist_in_the_synthetic_world() -> None:
    environment = default_environment()
    known_ids = (
        set(environment.customers)
        | set(environment.accounts)
        | set(environment.devices)
        | {outage.id for outage in environment.outages}
        | {ticket.id for ticket in environment.ticket_history}
        | {article.id for article in environment.articles}
    )
    assert all(
        source_id in known_ids
        for truth in load_hidden_truths()
        for source_id in truth.required_source_ids
    )


def test_observable_case_serialization_has_no_answer_key_fields() -> None:
    serialized = json.dumps([case.model_dump() for case in load_cases()]).lower()
    for forbidden in ("acceptable_root", "acceptable_action", "must_escalate", "required_tool", "forbidden_claim", "evaluator_note"):
        assert forbidden not in serialized


def test_support_world_contains_no_evaluation_truth_fields() -> None:
    world = Path("data/support_world.json").read_text(encoding="utf-8").lower()
    for forbidden in ("expected_diagnosis", "expected_resolution", "evaluator_score", "ground_truth"):
        assert forbidden not in world


def test_truth_identifiers_are_normalized() -> None:
    identifier = re.compile(r"^(?:[a-z][a-z0-9_]*|INSUFFICIENT_EVIDENCE)$")
    for truth in load_hidden_truths():
        assert all(identifier.fullmatch(value) for value in truth.acceptable_root_causes)
        assert all(identifier.fullmatch(value) for value in truth.acceptable_actions)


def test_perfect_candidate_passes() -> None:
    case = load_cases()[0]
    truth = load_hidden_truths()[0]
    assert score_case(case, truth, _perfect_candidate(case.case_id)).passed


def test_incorrect_diagnosis_fails() -> None:
    case = load_cases()[0]
    candidate = _perfect_candidate(case.case_id).model_copy(update={"root_cause_id": "hardware_failure"})
    score = score_case(case, load_hidden_truths()[0], candidate)
    assert not score.diagnosis_correct and not score.passed


def test_incorrect_action_fails() -> None:
    case = load_cases()[0]
    candidate = _perfect_candidate(case.case_id).model_copy(update={"recommended_action_id": "guide_gateway_activation"})
    score = score_case(case, load_hidden_truths()[0], candidate)
    assert not score.action_correct and not score.passed


def test_incorrect_escalation_fails() -> None:
    case = load_cases()[0]
    candidate = _perfect_candidate(case.case_id).model_copy(update={"escalate": True})
    score = score_case(case, load_hidden_truths()[0], candidate)
    assert not score.escalation_correct and not score.passed


def test_correct_abstention_passes_must_abstain_case() -> None:
    case = next(case for case in load_cases() if case.case_id == "CASE-011")
    truth = next(truth for truth in load_hidden_truths() if truth.case_id == case.case_id)
    assert score_case(case, truth, _perfect_candidate(case.case_id)).passed


def test_unjustified_guessing_fails_must_abstain_case() -> None:
    case = next(case for case in load_cases() if case.case_id == "CASE-011")
    truth = next(truth for truth in load_hidden_truths() if truth.case_id == case.case_id)
    candidate = _perfect_candidate(case.case_id).model_copy(update={"root_cause_id": "regional_outage"})
    assert not score_case(case, truth, candidate).passed


def test_missing_required_evidence_fails() -> None:
    case = load_cases()[0]
    candidate = _perfect_candidate(case.case_id).model_copy(update={"evidence_references": []})
    score = score_case(case, load_hidden_truths()[0], candidate)
    assert not score.evidence_coverage and not score.passed


def test_forbidden_critical_claim_fails() -> None:
    case = load_cases()[0]
    candidate = _perfect_candidate(case.case_id).model_copy(update={"asserted_claim_ids": ["hardware_failure"]})
    score = score_case(case, load_hidden_truths()[0], candidate)
    assert score.forbidden_claim_violations == ["hardware_failure"]
    assert not score.passed


def test_benchmark_scoring_is_repeatable() -> None:
    cases = load_cases()
    candidates = {case.case_id: _perfect_candidate(case.case_id) for case in cases}
    first = score_benchmark(cases, load_hidden_truths(), candidates).model_dump()
    second = score_benchmark(cases, load_hidden_truths(), candidates).model_dump()
    assert first == second


def test_benchmark_summary_statistics_are_correct() -> None:
    cases = load_cases()
    candidates = {case.case_id: _perfect_candidate(case.case_id) for case in cases}
    result = score_benchmark(cases, load_hidden_truths(), candidates)
    assert result.summary.total_cases == 15
    assert result.summary.passed_cases == 15
    assert result.summary.vrsr_percent == 100
    assert result.summary.forbidden_claim_violation_count == 0


def test_runtime_metrics_are_summarized_only_when_supplied() -> None:
    case = load_cases()[0]
    result = score_benchmark(
        [case],
        [load_hidden_truths()[0]],
        {case.case_id: _perfect_candidate(case.case_id)},
        {case.case_id: RuntimeMetrics(latency_ms=125, model_cost_usd=0.02, token_usage=50, retries=1, tool_call_count=3)},
    )
    assert result.summary.runtime_summary.model_dump() == {
        "average_latency_ms": 125.0,
        "total_model_cost_usd": 0.02,
        "total_token_usage": 50,
        "total_retries": 1,
        "total_tool_call_count": 3,
    }
