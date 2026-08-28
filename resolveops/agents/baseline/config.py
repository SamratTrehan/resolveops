"""Runtime configuration for the baseline; no model is hard-coded in agent logic."""

import os
from dataclasses import dataclass
from typing import Literal


DEFAULT_MODEL = "gpt-5.6-terra"
DEFAULT_REASONING_EFFORT = "medium"
ReasoningEffort = Literal["none", "minimal", "low", "medium", "high", "xhigh", "max"]
ALLOWED_REASONING_EFFORTS = ("none", "minimal", "low", "medium", "high", "xhigh", "max")


@dataclass(frozen=True)
class BaselineConfig:
    model: str = DEFAULT_MODEL
    reasoning_effort: ReasoningEffort = DEFAULT_REASONING_EFFORT

    def __post_init__(self) -> None:
        if not self.model.strip():
            raise ValueError("model must not be empty.")
        if self.reasoning_effort not in ALLOWED_REASONING_EFFORTS:
            raise ValueError(
                "RESOLVEOPS_REASONING_EFFORT must be one of: "
                + ", ".join(ALLOWED_REASONING_EFFORTS)
            )

    @classmethod
    def from_environment(cls) -> "BaselineConfig":
        return cls(
            model=os.environ.get("RESOLVEOPS_MODEL", DEFAULT_MODEL).strip(),
            reasoning_effort=os.environ.get(
                "RESOLVEOPS_REASONING_EFFORT", DEFAULT_REASONING_EFFORT
            ).strip().lower(),
        )
