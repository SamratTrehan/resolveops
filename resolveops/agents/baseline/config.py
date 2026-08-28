"""Runtime configuration for the baseline; no model is hard-coded in agent logic."""

import os
from dataclasses import dataclass
from typing import Literal

from resolveops.agents.baseline.prompt import BASELINE_V2_PROMPT_ID, instructions_for


DEFAULT_MODEL = "gpt-5.6-terra"
DEFAULT_REASONING_EFFORT = "medium"
ReasoningEffort = Literal["none", "minimal", "low", "medium", "high", "xhigh", "max"]
ALLOWED_REASONING_EFFORTS = ("none", "minimal", "low", "medium", "high", "xhigh", "max")
PromptId = Literal["baseline-v1", "baseline-v2"]


@dataclass(frozen=True)
class BaselineConfig:
    model: str = DEFAULT_MODEL
    reasoning_effort: ReasoningEffort = DEFAULT_REASONING_EFFORT
    prompt_id: PromptId = BASELINE_V2_PROMPT_ID

    def __post_init__(self) -> None:
        if not self.model.strip():
            raise ValueError("model must not be empty.")
        if self.reasoning_effort not in ALLOWED_REASONING_EFFORTS:
            raise ValueError(
                "RESOLVEOPS_REASONING_EFFORT must be one of: "
                + ", ".join(ALLOWED_REASONING_EFFORTS)
            )
        instructions_for(self.prompt_id)

    @classmethod
    def from_environment(cls) -> "BaselineConfig":
        return cls(
            model=os.environ.get("RESOLVEOPS_MODEL", DEFAULT_MODEL).strip(),
            reasoning_effort=os.environ.get(
                "RESOLVEOPS_REASONING_EFFORT", DEFAULT_REASONING_EFFORT
            ).strip().lower(),
        )
