"""Data contracts for the fixed benchmark and deterministic scorer."""

import re

from pydantic import BaseModel, Field, field_validator


NORMALIZED_ID_PATTERN = r"^(?:[a-z][a-z0-9_]*|INSUFFICIENT_EVIDENCE)$"


class EvaluationCase(BaseModel):
    case_id: str = Field(pattern=r"^CASE-\d{3}$")
    ticket_text: str
    customer_id: str = Field(pattern=r"^CUS-\d{3}$")
    primary_device_id: str | None = Field(default=None, pattern=r"^DEV-\d{3}$")


class HiddenTruth(BaseModel):
    """Evaluator-only answer key. Never expose this to a future agent runtime."""

    case_id: str = Field(pattern=r"^CASE-\d{3}$")
    acceptable_root_causes: list[str] = Field(min_length=1)
    required_tools: list[str] = Field(default_factory=list)
    required_source_ids: list[str] = Field(default_factory=list)
    acceptable_actions: list[str] = Field(min_length=1)
    must_escalate: bool
    acceptable_abstention: bool = False
    forbidden_claims: list[str] = Field(default_factory=list)
    evaluator_notes: str

    @field_validator("acceptable_root_causes", "acceptable_actions", "forbidden_claims")
    @classmethod
    def normalized_identifiers(cls, values: list[str]) -> list[str]:
        if any(not re.fullmatch(NORMALIZED_ID_PATTERN, value) for value in values):
            raise ValueError("Truth identifiers must be normalized.")
        return values


class EvidenceReference(BaseModel):
    tool_name: str
    source_id: str | None = None


class CandidateDraft(BaseModel):
    root_cause_id: str = Field(pattern=NORMALIZED_ID_PATTERN)
    confidence: float = Field(ge=0, le=1)
    recommended_action_id: str = Field(pattern=NORMALIZED_ID_PATTERN)
    escalate: bool
    evidence_references: list[EvidenceReference] = Field(default_factory=list)
    asserted_claim_ids: list[str] = Field(default_factory=list)
    customer_response: str
    internal_notes: str

    @field_validator("asserted_claim_ids")
    @classmethod
    def normalized_claims(cls, values: list[str]) -> list[str]:
        if any(not re.fullmatch(NORMALIZED_ID_PATTERN, value) for value in values):
            raise ValueError("Claim identifiers must be normalized.")
        return values


class CandidateOutput(CandidateDraft):
    case_id: str = Field(pattern=r"^CASE-\d{3}$")


class RuntimeMetrics(BaseModel):
    latency_ms: float | None = Field(default=None, ge=0)
    model_cost_usd: float | None = Field(default=None, ge=0)
    token_usage: int | None = Field(default=None, ge=0)
    retries: int | None = Field(default=None, ge=0)
    tool_call_count: int | None = Field(default=None, ge=0)


class CaseScore(BaseModel):
    case_id: str
    diagnosis_correct: bool
    action_correct: bool
    escalation_correct: bool
    evidence_coverage: bool
    forbidden_claim_violations: list[str] = Field(default_factory=list)
    passed: bool
    runtime_metrics: RuntimeMetrics | None = None


class RuntimeSummary(BaseModel):
    average_latency_ms: float | None = None
    total_model_cost_usd: float | None = None
    total_token_usage: int | None = None
    total_retries: int | None = None
    total_tool_call_count: int | None = None


class BenchmarkSummary(BaseModel):
    total_cases: int
    passed_cases: int
    vrsr_percent: float
    diagnosis_accuracy: float
    action_accuracy: float
    escalation_accuracy: float
    evidence_coverage: float
    forbidden_claim_violation_count: int
    forbidden_claim_violation_rate: float
    runtime_summary: RuntimeSummary | None = None


class BenchmarkScore(BaseModel):
    case_scores: list[CaseScore]
    summary: BenchmarkSummary
