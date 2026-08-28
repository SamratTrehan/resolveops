"""Authoritative orchestration metadata for investigator output."""

from resolveops.agents.resolveops.schemas import EvidenceBundle, EvidenceBundleDraft
from resolveops.evaluation.models import EvaluationCase


def with_authoritative_evidence_case_id(case: EvaluationCase, draft: EvidenceBundleDraft) -> EvidenceBundle:
    return EvidenceBundle(case_id=case.case_id, **draft.model_dump())
