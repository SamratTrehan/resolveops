"""Public benchmark contracts and deterministic scoring APIs."""

from .benchmark import load_cases, validate_benchmark_integrity
from .candidate import with_authoritative_case_id
from .models import CandidateDraft, CandidateOutput, EvaluationCase, EvidenceReference, RuntimeMetrics
from .scoring import score_benchmark, score_case

__all__ = [
    "CandidateOutput",
    "CandidateDraft",
    "EvaluationCase",
    "EvidenceReference",
    "RuntimeMetrics",
    "with_authoritative_case_id",
    "load_cases",
    "score_benchmark",
    "score_case",
    "validate_benchmark_integrity",
]
