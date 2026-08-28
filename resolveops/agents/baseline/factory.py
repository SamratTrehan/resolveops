"""Factory for exactly one general-purpose baseline agent."""

from agents import Agent, ModelSettings
from openai.types.shared import Reasoning

from resolveops.agents.baseline.config import BaselineConfig
from resolveops.agents.baseline.prompt import BASELINE_INSTRUCTIONS
from resolveops.agents.baseline.tools import BASELINE_TOOLS, BaselineRunContext
from resolveops.evaluation.models import CandidateDraft


BASELINE_AGENT_NAME = "ResolveOps Baseline"


def create_baseline_agent(config: BaselineConfig) -> Agent[BaselineRunContext]:
    return Agent(
        name=BASELINE_AGENT_NAME,
        instructions=BASELINE_INSTRUCTIONS,
        model=config.model,
        model_settings=ModelSettings(reasoning=Reasoning(effort=config.reasoning_effort)),
        tools=BASELINE_TOOLS,
        output_type=CandidateDraft,
    )
