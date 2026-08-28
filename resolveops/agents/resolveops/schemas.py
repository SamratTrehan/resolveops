"""Public structured handoff contracts for ResolveOps agents."""

from pydantic import BaseModel, ConfigDict, Field

from resolveops.evaluation.models import EvidenceReference


class ObservedFact(BaseModel):
    statement: str = Field(min_length=1)
    evidence_references: list[EvidenceReference] = Field(min_length=1)


class Hypothesis(BaseModel):
    label: str = Field(min_length=1)
    rationale: str = Field(min_length=1)


class EvidenceBundleDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ticket_summary: str = Field(min_length=1)
    observed_facts: list[ObservedFact] = Field(default_factory=list)
    evidence_references: list[EvidenceReference] = Field(default_factory=list)
    hypotheses: list[Hypothesis] = Field(default_factory=list)
    contradictions: list[str] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)
    investigation_summary: str = Field(min_length=1)


class EvidenceBundle(EvidenceBundleDraft):
    case_id: str = Field(pattern=r"^CASE-\d{3}$")
