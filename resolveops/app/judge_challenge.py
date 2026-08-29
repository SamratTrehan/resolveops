"""Session-only fresh inference for the synthetic Judge Challenge."""

import logging
import os
from collections.abc import Callable, Mapping, MutableMapping
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from agents import OpenAIProvider, RunConfig, Runner
from pydantic import BaseModel

from resolveops.agents.baseline.config import BaselineConfig
from resolveops.agents.resolveops.records import AgentTrajectory
from resolveops.agents.resolveops.runner import run_case
from resolveops.agents.resolveops.safety import SafetyGateRecord
from resolveops.evaluation.benchmark import load_cases
from resolveops.evaluation.models import CandidateOutput, EvaluationCase
from resolveops.tools import default_environment


MAX_FRESH_RUNS_PER_SESSION = 3
FRESH_RUN_COUNT_KEY = "judge_challenge_run_count"
FRESH_RESULT_KEY = "judge_challenge_result"
FRESH_ERROR_KEY = "judge_challenge_error"
MAX_TICKET_LENGTH = 2_000
LOGGER = logging.getLogger(__name__)


class ChallengeUnavailable(RuntimeError):
    pass


class ChallengeAllowanceUsed(RuntimeError):
    pass


class ChallengeExecutionError(RuntimeError):
    pass


class FreshRunResult(BaseModel):
    run_id: str
    started_at: datetime
    case: EvaluationCase
    model: str
    reasoning_effort: str
    candidate: CandidateOutput
    stages: list[AgentTrajectory]
    safety_gate: SafetyGateRecord
    benchmark_scored: bool = False


def configured_server_key(secrets: object, environ: Mapping[str, str] | None = None) -> str | None:
    """Prefer Streamlit secrets, with an environment fallback for local development."""
    try:
        secret = secrets.get("OPENAI_API_KEY")  # type: ignore[attr-defined]
    except Exception:
        secret = None
    environment = os.environ if environ is None else environ
    value = secret or environment.get("OPENAI_API_KEY")
    return value.strip() if isinstance(value, str) and value.strip() else None


def challenge_templates() -> list[EvaluationCase]:
    """Return observable cases whose customer/device relationships exist in the public world."""
    environment = default_environment()
    cases = load_cases()
    for case in cases:
        if case.customer_id not in environment.customers:
            raise ValueError(f"Unknown synthetic customer: {case.customer_id}")
        if case.primary_device_id:
            device = environment.devices.get(case.primary_device_id)
            if not device or environment.accounts[device.account_id].customer_id != case.customer_id:
                raise ValueError(f"Invalid synthetic device/customer pairing: {case.case_id}")
    return cases


def challenge_case(template_case_id: str, ticket_text: str) -> EvaluationCase:
    templates = {case.case_id: case for case in challenge_templates()}
    if template_case_id not in templates:
        raise ValueError("Unknown Judge Challenge template.")
    cleaned = ticket_text.strip()
    if not cleaned:
        raise ValueError("Ticket text must not be empty.")
    if len(cleaned) > MAX_TICKET_LENGTH:
        raise ValueError(f"Ticket text must be {MAX_TICKET_LENGTH} characters or fewer.")
    return templates[template_case_id].model_copy(update={"ticket_text": cleaned})


def fresh_runs_consumed(state: Mapping[str, object]) -> int:
    return int(state.get(FRESH_RUN_COUNT_KEY, 0))


def fresh_runs_remaining(state: Mapping[str, object]) -> int:
    return max(0, MAX_FRESH_RUNS_PER_SESSION - fresh_runs_consumed(state))


def fresh_allowance_available(state: Mapping[str, object]) -> bool:
    return fresh_runs_remaining(state) > 0


def _sdk_run_sync(api_key: str) -> Callable[..., Any]:
    provider = OpenAIProvider(api_key=api_key)
    run_config = RunConfig(
        model_provider=provider,
        tracing_disabled=True,
        trace_include_sensitive_data=False,
    )

    def invoke(agent: object, user_input: str, **kwargs: object) -> object:
        return Runner.run_sync(agent, user_input, run_config=run_config, **kwargs)

    return invoke


def execute_challenge(
    case: EvaluationCase,
    api_key: str,
    run_sync: Callable[..., Any] | None = None,
    now: datetime | None = None,
    identifier: str | None = None,
) -> FreshRunResult:
    """Execute the production single-case workflow without creating artifacts."""
    if not api_key.strip():
        raise ChallengeUnavailable("Fresh inference is temporarily unavailable.")
    started_at = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    run_id = f"judge-{started_at:%Y%m%d}-{identifier or uuid4().hex[:8]}"
    config = BaselineConfig.from_environment()
    candidate, stages = run_case(
        case,
        config,
        run_id,
        run_sync=run_sync or _sdk_run_sync(api_key),
    )
    if candidate is None or not stages or stages[-1].safety_gate is None:
        raise ChallengeExecutionError("Fresh inference did not complete.")
    return FreshRunResult(
        run_id=run_id,
        started_at=started_at,
        case=case,
        model=config.model,
        reasoning_effort=config.reasoning_effort,
        candidate=candidate,
        stages=stages,
        safety_gate=stages[-1].safety_gate,
    )


def run_challenge_once(
    state: MutableMapping[str, object],
    template_case_id: str,
    ticket_text: str,
    api_key: str | None,
    run_sync: Callable[..., Any] | None = None,
) -> FreshRunResult:
    """Validate first, then consume one session allowance immediately before execution."""
    if not api_key:
        raise ChallengeUnavailable("Fresh inference is temporarily unavailable.")
    if not fresh_allowance_available(state):
        raise ChallengeAllowanceUsed("Fresh run allowance used for this session.")
    case = challenge_case(template_case_id, ticket_text)
    state[FRESH_RUN_COUNT_KEY] = fresh_runs_consumed(state) + 1
    state.pop(FRESH_ERROR_KEY, None)
    try:
        result = execute_challenge(case, api_key, run_sync=run_sync)
    except Exception as error:
        LOGGER.warning("Judge Challenge execution failed (%s).", type(error).__name__)
        state[FRESH_ERROR_KEY] = "Fresh inference did not complete."
        raise ChallengeExecutionError("Fresh inference did not complete.") from None
    state[FRESH_RESULT_KEY] = result.model_dump(mode="json")
    return result


def stage_mapping(result: FreshRunResult) -> dict[str, dict[str, object]]:
    return {stage.prompt_id: stage.model_dump(mode="json") for stage in result.stages}


def resolution_packet_export(result: FreshRunResult) -> dict[str, object]:
    return {
        "label": "Fresh demonstration run — not benchmark-scored.",
        "run_id": result.run_id,
        "started_at": result.started_at.isoformat(),
        "model": result.model,
        "reasoning_effort": result.reasoning_effort,
        "benchmark_scored": False,
        "resolution_packet": result.candidate.model_dump(mode="json"),
        "safety_gate": result.safety_gate.model_dump(mode="json"),
    }
