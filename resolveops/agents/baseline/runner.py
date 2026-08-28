"""Generation-only baseline runner. Evaluator-only scoring is intentionally separate."""

import argparse
import os
import time
from collections.abc import Callable
from typing import Any

from agents import Runner
from agents.exceptions import ModelBehaviorError

from resolveops.agents.baseline.artifacts import ArtifactStore, FailedRunRecord, RunManifest
from resolveops.agents.baseline.config import BaselineConfig
from resolveops.agents.baseline.factory import BASELINE_AGENT_NAME, create_baseline_agent
from resolveops.agents.baseline.records import BaselineAttempt, BaselineTrajectory, RuntimeRecord
from resolveops.agents.baseline.tools import BaselineRunContext
from resolveops.evaluation.benchmark import load_cases
from resolveops.evaluation.candidate import with_authoritative_case_id
from resolveops.evaluation.models import CandidateDraft, CandidateOutput, EvaluationCase, ExecutionFailure, RuntimeMetrics


class CaseRunError(RuntimeError):
    def __init__(self, trajectory: BaselineTrajectory) -> None:
        super().__init__(f"Baseline run failed for {trajectory.case_id}")
        self.trajectory = trajectory


MAX_INFRASTRUCTURE_RETRIES = 1


def _case_input(case: EvaluationCase) -> str:
    return (
        f"Ticket:\n{case.ticket_text}\n\n"
        f"Customer ID: {case.customer_id}\n"
        f"Primary device ID: {case.primary_device_id or 'None'}"
    )


def _usage_data(result: object) -> dict[str, int] | None:
    usage = getattr(getattr(result, "context_wrapper", None), "usage", None)
    if not usage or not getattr(usage, "requests", 0):
        return None
    output_details = getattr(usage, "output_tokens_details", None)
    return {
        "input_tokens": getattr(usage, "input_tokens", 0),
        "output_tokens": getattr(usage, "output_tokens", 0),
        "reasoning_tokens": getattr(output_details, "reasoning_tokens", 0) if output_details else 0,
        "total_tokens": getattr(usage, "total_tokens", 0),
    }


def _is_retryable_structured_output_error(error: Exception) -> bool:
    """Retry only the SDK's malformed structured-JSON response failure."""
    return isinstance(error, ModelBehaviorError) and "invalid json when parsing model output" in str(error).lower()


def _aggregate_usage(attempts: list[BaselineAttempt]) -> dict[str, int] | None:
    if not attempts or any(attempt.usage is None for attempt in attempts):
        return None
    return {
        key: sum(attempt.usage[key] for attempt in attempts if attempt.usage is not None)
        for key in ("input_tokens", "output_tokens", "reasoning_tokens", "total_tokens")
    }


def _aggregate_metrics(attempts: list[BaselineAttempt], retries: int) -> RuntimeMetrics:
    usage = _aggregate_usage(attempts)
    return RuntimeMetrics(
        latency_ms=sum(attempt.runtime_metrics.latency_ms or 0 for attempt in attempts),
        token_usage=usage["total_tokens"] if usage else None,
        retries=retries,
        tool_call_count=sum(len(attempt.tool_calls) for attempt in attempts),
    )


def run_case(
    case: EvaluationCase,
    config: BaselineConfig,
    run_id: str,
    run_sync: Callable[..., Any] = Runner.run_sync,
) -> tuple[CandidateOutput, BaselineTrajectory]:
    """Run the single SDK agent for one observable case and capture its local trajectory."""
    attempts: list[BaselineAttempt] = []
    for attempt_number in range(1, MAX_INFRASTRUCTURE_RETRIES + 2):
        context = BaselineRunContext()
        started = time.perf_counter()
        try:
            result = run_sync(create_baseline_agent(config), _case_input(case), context=context, max_turns=8)
            usage = _usage_data(result)
            attempt = BaselineAttempt(
                attempt_number=attempt_number,
                status="completed",
                model=config.model,
                reasoning_effort=config.reasoning_effort,
                prompt_id=config.prompt_id,
                tool_calls=context.tool_calls,
                runtime_metrics=RuntimeMetrics(
                    latency_ms=(time.perf_counter() - started) * 1000,
                    token_usage=usage["total_tokens"] if usage else None,
                    tool_call_count=len(context.tool_calls),
                ),
                usage=usage,
            )
            attempts.append(attempt)
            candidate = with_authoritative_case_id(case, CandidateDraft.model_validate(result.final_output))
            retries = len(attempts) - 1
            return candidate, BaselineTrajectory(
                run_id=run_id, case_id=case.case_id, model=config.model,
                reasoning_effort=config.reasoning_effort, agent_name=BASELINE_AGENT_NAME,
                prompt_id=config.prompt_id, status="completed", infrastructure_retries=retries,
                attempts=attempts, tool_calls=[call for item in attempts for call in item.tool_calls],
                final_output=candidate, runtime_metrics=_aggregate_metrics(attempts, retries),
                usage=_aggregate_usage(attempts),
            )
        except Exception as error:
            attempt = BaselineAttempt(
                attempt_number=attempt_number, status="failed", model=config.model,
                reasoning_effort=config.reasoning_effort, prompt_id=config.prompt_id,
                tool_calls=context.tool_calls, error=f"{type(error).__name__}: {error}",
                runtime_metrics=RuntimeMetrics(
                    latency_ms=(time.perf_counter() - started) * 1000,
                    tool_call_count=len(context.tool_calls),
                ),
            )
            attempts.append(attempt)
            if _is_retryable_structured_output_error(error) and attempt_number <= MAX_INFRASTRUCTURE_RETRIES:
                continue
            retries = len(attempts) - 1
            trajectory = BaselineTrajectory(
                run_id=run_id, case_id=case.case_id, model=config.model,
                reasoning_effort=config.reasoning_effort, agent_name=BASELINE_AGENT_NAME,
                prompt_id=config.prompt_id, status="failed", infrastructure_retries=retries,
                attempts=attempts, tool_calls=[call for item in attempts for call in item.tool_calls],
                error=attempt.error, runtime_metrics=_aggregate_metrics(attempts, retries),
                usage=_aggregate_usage(attempts),
            )
            raise CaseRunError(trajectory) from error


def run_cases(
    cases: list[EvaluationCase],
    config: BaselineConfig,
    run_id: str,
    official: bool = False,
    continue_on_execution_failure: bool = False,
) -> None:
    if official and len(cases) != len(load_cases()):
        raise ValueError("An official baseline run must include all fixed benchmark cases.")
    store = ArtifactStore(run_id)
    store.prepare()
    candidates: dict[str, CandidateOutput] = {}
    execution_failures: dict[str, ExecutionFailure] = {}
    runtime_metadata: dict[str, RuntimeRecord] = {}
    for case in cases:
        try:
            candidate, trajectory = run_case(case, config, run_id)
        except CaseRunError as error:
            store.write_trajectory(error.trajectory)
            if continue_on_execution_failure:
                cause = error.__cause__ or error
                execution_failures[case.case_id] = ExecutionFailure(
                    case_id=case.case_id,
                    error_type=type(cause).__name__,
                    error_message=str(cause),
                    infrastructure_retries=error.trajectory.infrastructure_retries,
                )
                runtime_metadata[case.case_id] = RuntimeRecord(
                    model=config.model,
                    reasoning_effort=config.reasoning_effort,
                    metrics=error.trajectory.runtime_metrics,
                )
                continue
            store.write_failure(
                candidates,
                runtime_metadata,
                FailedRunRecord(
                    run_id=run_id,
                    run_kind="official" if official else "development",
                    model=config.model,
                    reasoning_effort=config.reasoning_effort,
                    agent_name=BASELINE_AGENT_NAME,
                    prompt_id=config.prompt_id,
                    requested_case_ids=[item.case_id for item in cases],
                    completed_case_ids=list(candidates),
                    failed_case_id=case.case_id,
                    error_type=type(error.__cause__).__name__ if error.__cause__ else type(error).__name__,
                    error_message=str(error.__cause__ or error),
                ),
            )
            raise error
        store.write_trajectory(trajectory)
        candidates[case.case_id] = candidate
        runtime_metadata[case.case_id] = RuntimeRecord(
            model=config.model,
            reasoning_effort=config.reasoning_effort,
            metrics=trajectory.runtime_metrics,
        )
    store.write_results(
        candidates,
        runtime_metadata,
        execution_failures,
        RunManifest(
            run_id=run_id,
            run_kind="official" if official else "development",
            model=config.model,
            reasoning_effort=config.reasoning_effort,
            agent_name=BASELINE_AGENT_NAME,
            prompt_id=config.prompt_id,
            case_ids=[case.case_id for case in cases],
            successful_candidate_count=len(candidates),
            execution_failure_count=len(execution_failures),
        ),
    )


def _configuration(model_override: str | None) -> BaselineConfig:
    if model_override:
        return BaselineConfig(
            model=model_override,
            reasoning_effort=BaselineConfig.from_environment().reasoning_effort,
        )
    return BaselineConfig.from_environment()


def select_case(case_id: str) -> EvaluationCase:
    for case in load_cases():
        if case.case_id == case_id:
            return case
    raise ValueError(f"Unknown benchmark case ID: {case_id}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the single-agent ResolveOps baseline.")
    selection = parser.add_mutually_exclusive_group(required=True)
    selection.add_argument("--case-id")
    selection.add_argument("--all", action="store_true")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--model", help="Overrides RESOLVEOPS_MODEL for this run.")
    parser.add_argument("--official", action="store_true", help="Mark an all-case run as the future frozen official baseline.")
    args = parser.parse_args()
    if not os.environ.get("OPENAI_API_KEY"):
        parser.error("OPENAI_API_KEY must be set for a live baseline run.")
    cases = load_cases()
    if args.all:
        selected = cases
    else:
        try:
            selected = [select_case(args.case_id)]
        except ValueError as error:
            parser.error(str(error))
    if args.official and not args.all:
        parser.error("--official requires --all.")
    run_cases(
        selected,
        _configuration(args.model),
        args.run_id,
        official=args.official,
        continue_on_execution_failure=args.all,
    )


if __name__ == "__main__":
    main()
