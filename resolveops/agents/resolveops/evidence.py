"""Authoritative orchestration metadata for investigator output."""

from resolveops.agents.resolveops.schemas import EvidenceBundle, EvidenceBundleDraft, ObservedFact
from resolveops.evaluation.models import EvaluationCase
from resolveops.evaluation.models import EvidenceReference


def with_authoritative_evidence_case_id(case: EvaluationCase, draft: EvidenceBundleDraft) -> EvidenceBundle:
    return EvidenceBundle(case_id=case.case_id, **draft.model_dump())


def canonical_tool_name(name: str) -> str:
    return name.removeprefix("functions.")


def normalize_evidence_bundle(bundle: EvidenceBundle) -> EvidenceBundle:
    def reference(item: EvidenceReference) -> EvidenceReference:
        return item.model_copy(update={"tool_name": canonical_tool_name(item.tool_name)})
    return bundle.model_copy(update={
        "evidence_references": [reference(item) for item in bundle.evidence_references],
        "observed_facts": [fact.model_copy(update={"evidence_references": [reference(item) for item in fact.evidence_references]}) for fact in bundle.observed_facts],
    })
