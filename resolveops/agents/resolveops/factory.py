"""Phase 4 Investigator and Resolver factories."""

from agents import Agent, ModelSettings
from openai.types.shared import Reasoning

from resolveops.agents.baseline.config import BaselineConfig
from resolveops.agents.baseline.tools import BASELINE_TOOLS, BaselineRunContext
from resolveops.agents.resolveops.prompts import INVESTIGATOR_INSTRUCTIONS, RESOLVER_INSTRUCTIONS
from resolveops.agents.resolveops.schemas import EvidenceBundleDraft
from resolveops.evaluation.models import CandidateDraft


INVESTIGATOR_NAME = "ResolveOps Investigator"
RESOLVER_NAME = "ResolveOps Resolver"


def _settings(config: BaselineConfig) -> ModelSettings:
    return ModelSettings(reasoning=Reasoning(effort=config.reasoning_effort))


def create_investigator(config: BaselineConfig) -> Agent[BaselineRunContext]:
    return Agent(name=INVESTIGATOR_NAME, instructions=INVESTIGATOR_INSTRUCTIONS, model=config.model, model_settings=_settings(config), tools=BASELINE_TOOLS, output_type=EvidenceBundleDraft)


def create_resolver(config: BaselineConfig) -> Agent[None]:
    return Agent(name=RESOLVER_NAME, instructions=RESOLVER_INSTRUCTIONS, model=config.model, model_settings=_settings(config), tools=[], output_type=CandidateDraft)
