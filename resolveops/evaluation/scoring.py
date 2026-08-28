"""Strict, deterministic scoring for the fixed ResolveOps benchmark."""

from collections.abc import Mapping

from resolveops.evaluation.models import (
    BenchmarkScore,
    BenchmarkSummary,
    CandidateOutput,
    CaseScore,
    EvaluationCase,
    ExecutionFailure,
    HiddenTruth,
    RuntimeMetrics,
    RuntimeSummary,
)


def score_case(
    case: EvaluationCase,
    truth: HiddenTruth,
    candidate: CandidateOutput,
    runtime_metrics: RuntimeMetrics | None = None,
) -> CaseScore:
    """Score one candidate. All component gates must pass for VRSR success."""
    case_matches = case.case_id == truth.case_id == candidate.case_id
    diagnosis_correct = case_matches and candidate.root_cause_id in truth.acceptable_root_causes
    action_correct = case_matches and candidate.recommended_action_id in truth.acceptable_actions
    escalation_correct = case_matches and candidate.escalate == truth.must_escalate
    observed_tools = {reference.tool_name for reference in candidate.evidence_references}
    observed_source_ids = {reference.source_id for reference in candidate.evidence_references if reference.source_id}
    evidence_coverage = (
        case_matches
        and set(truth.required_tools).issubset(observed_tools)
        and set(truth.required_source_ids).issubset(observed_source_ids)
    )
    forbidden_claim_violations = sorted(set(candidate.asserted_claim_ids) & set(truth.forbidden_claims))
    passed = all((diagnosis_correct, action_correct, escalation_correct, evidence_coverage)) and not forbidden_claim_violations
    return CaseScore(
        case_id=case.case_id,
        diagnosis_correct=diagnosis_correct,
        action_correct=action_correct,
        escalation_correct=escalation_correct,
        evidence_coverage=evidence_coverage,
        forbidden_claim_violations=forbidden_claim_violations,
        passed=passed,
        runtime_metrics=runtime_metrics,
    )


def score_execution_failure(case: EvaluationCase, runtime_metrics: RuntimeMetrics | None = None) -> CaseScore:
    """Score an exhausted runtime failure without inventing a candidate."""
    return CaseScore(
        case_id=case.case_id,
        execution_failure=True,
        diagnosis_correct=False,
        action_correct=False,
        escalation_correct=False,
        evidence_coverage=False,
        passed=False,
        runtime_metrics=runtime_metrics,
    )


def _runtime_summary(metrics: list[RuntimeMetrics]) -> RuntimeSummary | None:
    if not metrics:
        return None

    def average(field: str) -> float | None:
        values = [getattr(metric, field) for metric in metrics if getattr(metric, field) is not None]
        return sum(values) / len(values) if values else None

    def total(field: str) -> int | float | None:
        values = [getattr(metric, field) for metric in metrics if getattr(metric, field) is not None]
        return sum(values) if values else None

    return RuntimeSummary(
        average_latency_ms=average("latency_ms"),
        total_model_cost_usd=total("model_cost_usd"),
        total_token_usage=total("token_usage"),
        total_retries=total("retries"),
        total_tool_call_count=total("tool_call_count"),
    )


def score_benchmark(
    cases: list[EvaluationCase],
    truths: list[HiddenTruth],
    candidates: Mapping[str, CandidateOutput],
    runtime_metrics: Mapping[str, RuntimeMetrics] | None = None,
    execution_failures: Mapping[str, ExecutionFailure] | None = None,
) -> BenchmarkScore:
    truths_by_id = {truth.case_id: truth for truth in truths}
    if {case.case_id for case in cases} != set(truths_by_id):
        raise ValueError("Cases and truths must have identical case IDs before scoring.")
    execution_failures = execution_failures or {}
    if set(candidates) & set(execution_failures):
        raise ValueError("A case cannot have both a candidate and an execution failure.")
    scores = [
        score_execution_failure(case, runtime_metrics.get(case.case_id) if runtime_metrics else None)
        if case.case_id in execution_failures else score_case(
                case,
                truths_by_id[case.case_id],
                candidates.get(case.case_id, CandidateOutput(
                    case_id=case.case_id,
                    root_cause_id="INSUFFICIENT_EVIDENCE",
                    confidence=0,
                    recommended_action_id="INSUFFICIENT_EVIDENCE",
                    escalate=False,
                    customer_response="No candidate supplied.",
                    internal_notes="No candidate supplied.",
                )),
                runtime_metrics.get(case.case_id) if runtime_metrics else None,
            )
        for case in cases
    ]
    total = len(scores)
    passed = sum(score.passed for score in scores)
    violations = sum(len(score.forbidden_claim_violations) for score in scores)
    percent = lambda value: 100 * value / total if total else 0.0
    summary = BenchmarkSummary(
        total_cases=total,
        passed_cases=passed,
        vrsr_percent=percent(passed),
        diagnosis_accuracy=percent(sum(score.diagnosis_correct for score in scores)),
        action_accuracy=percent(sum(score.action_correct for score in scores)),
        escalation_accuracy=percent(sum(score.escalation_correct for score in scores)),
        evidence_coverage=percent(sum(score.evidence_coverage for score in scores)),
        forbidden_claim_violation_count=violations,
        forbidden_claim_violation_rate=percent(sum(bool(score.forbidden_claim_violations) for score in scores)),
        runtime_summary=_runtime_summary([score.runtime_metrics for score in scores if score.runtime_metrics]),
    )
    return BenchmarkScore(case_scores=scores, summary=summary)
