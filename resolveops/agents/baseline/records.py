"""Serializable local records for baseline runs and tool use."""

from pydantic import BaseModel, Field

from resolveops.domain import ToolResult
from resolveops.evaluation.models import CandidateOutput, RuntimeMetrics


class RecordedToolCall(BaseModel):
    tool_name: str
    arguments: dict[str, object]
    result: ToolResult


class BaselineTrajectory(BaseModel):
    run_id: str
    case_id: str
    model: str
    reasoning_effort: str
    agent_name: str
    prompt_id: str
    status: str
    tool_calls: list[RecordedToolCall] = Field(default_factory=list)
    final_output: CandidateOutput | None = None
    error: str | None = None
    runtime_metrics: RuntimeMetrics
    usage: dict[str, int] | None = None


class RuntimeRecord(BaseModel):
    model: str
    reasoning_effort: str
    metrics: RuntimeMetrics
