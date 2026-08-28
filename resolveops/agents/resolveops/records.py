"""Serializable Phase 4 agent trajectories."""

from pydantic import BaseModel, Field

from resolveops.agents.baseline.records import RecordedToolCall
from resolveops.evaluation.models import RuntimeMetrics


class AgentAttempt(BaseModel):
    attempt_number: int = Field(ge=1)
    status: str
    tool_calls: list[RecordedToolCall] = Field(default_factory=list)
    error: str | None = None
    runtime_metrics: RuntimeMetrics
    usage: dict[str, int] | None = None


class AgentTrajectory(BaseModel):
    run_id: str
    case_id: str
    agent_name: str
    prompt_id: str
    model: str
    reasoning_effort: str
    input_summary: str
    status: str
    attempts: list[AgentAttempt] = Field(default_factory=list)
    tool_calls: list[RecordedToolCall] = Field(default_factory=list)
    output: dict[str, object] | None = None
    error: str | None = None
    runtime_metrics: RuntimeMetrics
    usage: dict[str, int] | None = None
