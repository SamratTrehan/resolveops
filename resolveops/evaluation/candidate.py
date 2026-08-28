"""Deterministic construction helpers for public candidate outputs."""

from resolveops.evaluation.models import CandidateDraft, CandidateOutput, EvaluationCase


def with_authoritative_case_id(case: EvaluationCase, candidate: CandidateDraft) -> CandidateOutput:
    """Attach runner-owned case metadata without changing model reasoning fields."""
    return CandidateOutput(case_id=case.case_id, **candidate.model_dump())
