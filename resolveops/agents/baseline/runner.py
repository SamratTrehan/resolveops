"""Generation-only baseline runner. Evaluator-only scoring is intentionally separate."""

import argparse
import os
import time

from agents import Runner

from resolveops.agents.baseline.artifacts import ArtifactStore, RunManifest
from resolveops.agents.baseline.config import BaselineConfig
from resolveops.agents.baseline.factory import BASELINE_AGENT_NAME, create_baseline_agent
from resolveops.agents.baseline.prompt import BASELINE_PROMPT_ID
from resolveops.agents.baseline.records import BaselineTrajectory, RuntimeRecord
from resolveops.agents.baseline.tools import BaselineRunContext
from resolveops.evaluation.benchmark import load_cases
from resolveops.evaluation.candidate import with_authoritative_case_id
from resolveops.evaluation.models import CandidateDraft, CandidateOutput, EvaluationCase, RuntimeMetrics


class CaseRunError(RuntimeError):
    def __init__(self, trajectory: BaselineTrajectory) -> None:
        super().__init__(f"Baseline run failed for {trajectory.case_id}")
        self.trajectory = trajectory


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


def run_case(case: EvaluationCase, config: BaselineConfig, run_id: str) -> tuple[CandidateOutput, BaselineTrajectory]:
    """Run the single SDK agent for one observable case and capture its local trajectory."""
    context = BaselineRunContext()
    started = time.perf_counter()
    try:
        result = Runner.run_sync(create_baseline_agent(config), _case_input(case), context=context, max_turns=8)
        candidate = with_authoritative_case_id(
            case,
            CandidateDraft.model_validate(result.final_output),
        )
        elapsed_ms = (time.perf_counter() - started) * 1000
        usage = _usage_data(result)
        metrics = RuntimeMetrics(
            latency_ms=elapsed_ms,
            token_usage=usage["total_tokens"] if usage else None,
            retries=0,
            tool_call_count=len(context.tool_calls),
        )
        return candidate, BaselineTrajectory(
            run_id=run_id,
            case_id=case.case_id,
            model=config.model,
            reasoning_effort=config.reasoning_effort,
            agent_name=BASELINE_AGENT_NAME,
            prompt_id=BASELINE_PROMPT_ID,
            status="completed",
            tool_calls=context.tool_calls,
            final_output=candidate,
            runtime_metrics=metrics,
            usage=usage,
        )
    except Exception as error:
        elapsed_ms = (time.perf_counter() - started) * 1000
        trajectory = BaselineTrajectory(
            run_id=run_id,
            case_id=case.case_id,
            model=config.model,
            reasoning_effort=config.reasoning_effort,
            agent_name=BASELINE_AGENT_NAME,
            prompt_id=BASELINE_PROMPT_ID,
            status="failed",
            tool_calls=context.tool_calls,
            error=f"{type(error).__name__}: {error}",
            runtime_metrics=RuntimeMetrics(latency_ms=elapsed_ms, retries=0, tool_call_count=len(context.tool_calls)),
        )
        raise CaseRunError(trajectory) from error


def run_cases(cases: list[EvaluationCase], config: BaselineConfig, run_id: str, official: bool = False) -> None:
    if official and len(cases) != len(load_cases()):
        raise ValueError("An official baseline run must include all fixed benchmark cases.")
    store = ArtifactStore(run_id)
    store.prepare()
    candidates: dict[str, CandidateOutput] = {}
    runtime_metadata: dict[str, RuntimeRecord] = {}
    for case in cases:
        try:
            candidate, trajectory = run_case(case, config, run_id)
        except CaseRunError as error:
            store.write_trajectory(error.trajectory)
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
        RunManifest(
            run_id=run_id,
            run_kind="official" if official else "development",
            model=config.model,
            reasoning_effort=config.reasoning_effort,
            agent_name=BASELINE_AGENT_NAME,
            prompt_id=BASELINE_PROMPT_ID,
            case_ids=[case.case_id for case in cases],
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
    run_cases(selected, _configuration(args.model), args.run_id, official=args.official)


if __name__ == "__main__":
    main()
