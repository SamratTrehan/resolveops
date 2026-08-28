"""Phase 4 Investigator-to-Resolver generation runner; scoring stays separate."""

import argparse
import json
import os
import time
from collections.abc import Callable
from typing import Any

from agents import Runner
from agents.exceptions import ModelBehaviorError

from resolveops.agents.baseline.config import BaselineConfig
from resolveops.agents.baseline.records import RuntimeRecord
from resolveops.agents.baseline.runner import MAX_INFRASTRUCTURE_RETRIES, _usage_data, select_case
from resolveops.agents.baseline.tools import BaselineRunContext
from resolveops.agents.resolveops.artifacts import ResolveOpsArtifactStore, ResolveOpsManifest
from resolveops.agents.resolveops.evidence import with_authoritative_evidence_case_id
from resolveops.agents.resolveops.factory import INVESTIGATOR_NAME, RESOLVER_NAME, create_investigator, create_resolver
from resolveops.agents.resolveops.prompts import INVESTIGATOR_PROMPT_ID, RESOLVER_PROMPT_ID
from resolveops.agents.resolveops.records import AgentAttempt, AgentTrajectory
from resolveops.agents.resolveops.schemas import EvidenceBundle, EvidenceBundleDraft
from resolveops.evaluation.benchmark import load_cases
from resolveops.evaluation.candidate import with_authoritative_case_id
from resolveops.evaluation.models import CandidateDraft, CandidateOutput, EvaluationCase, ExecutionFailure, RuntimeMetrics


def _retryable(error: Exception) -> bool:
    return isinstance(error, ModelBehaviorError) and "invalid json when parsing model output" in str(error).lower()


def _input(case: EvaluationCase) -> str:
    return f"Ticket:\n{case.ticket_text}\n\nCustomer ID: {case.customer_id}\nPrimary device ID: {case.primary_device_id or 'None'}"


def _metrics(attempts: list[AgentAttempt]) -> RuntimeMetrics:
    return RuntimeMetrics(latency_ms=sum(item.runtime_metrics.latency_ms or 0 for item in attempts), retries=len(attempts) - 1, tool_call_count=sum(len(item.tool_calls) for item in attempts))


def _run_agent(case: EvaluationCase, config: BaselineConfig, run_id: str, name: str, prompt_id: str, agent_factory: Callable[[BaselineConfig], Any], user_input: str, uses_tools: bool, run_sync: Callable[..., Any]) -> tuple[Any | None, AgentTrajectory]:
    attempts: list[AgentAttempt] = []
    for number in range(1, MAX_INFRASTRUCTURE_RETRIES + 2):
        attempt_context = BaselineRunContext()
        started = time.perf_counter()
        try:
            result = run_sync(agent_factory(config), user_input, context=attempt_context, max_turns=8)
            usage = _usage_data(result)
            attempts.append(AgentAttempt(attempt_number=number, status="completed", tool_calls=attempt_context.tool_calls, runtime_metrics=RuntimeMetrics(latency_ms=(time.perf_counter()-started)*1000, token_usage=usage["total_tokens"] if usage else None, tool_call_count=len(attempt_context.tool_calls)), usage=usage))
            output = result.final_output
            return output, AgentTrajectory(run_id=run_id, case_id=case.case_id, agent_name=name, prompt_id=prompt_id, model=config.model, reasoning_effort=config.reasoning_effort, input_summary=user_input, status="completed", attempts=attempts, tool_calls=[call for attempt in attempts for call in attempt.tool_calls], output=output.model_dump(mode="json"), runtime_metrics=_metrics(attempts), usage=usage)
        except Exception as error:
            attempts.append(AgentAttempt(attempt_number=number, status="failed", tool_calls=attempt_context.tool_calls, error=f"{type(error).__name__}: {error}", runtime_metrics=RuntimeMetrics(latency_ms=(time.perf_counter()-started)*1000, tool_call_count=len(attempt_context.tool_calls))))
            if _retryable(error) and number <= MAX_INFRASTRUCTURE_RETRIES:
                continue
            return None, AgentTrajectory(run_id=run_id, case_id=case.case_id, agent_name=name, prompt_id=prompt_id, model=config.model, reasoning_effort=config.reasoning_effort, input_summary=user_input, status="failed", attempts=attempts, tool_calls=[call for attempt in attempts for call in attempt.tool_calls], error=attempts[-1].error, runtime_metrics=_metrics(attempts))


def _validate_bundle(bundle: EvidenceBundle, calls: list[Any]) -> None:
    available = {(call.tool_name, source_id) for call in calls for source_id in call.result.source_ids}
    references = [reference for fact in bundle.observed_facts for reference in fact.evidence_references] + bundle.evidence_references
    if any((reference.tool_name, reference.source_id) not in available for reference in references if reference.source_id):
        raise ValueError("EvidenceBundle contains a reference not returned by an investigator tool.")


def run_case(case: EvaluationCase, config: BaselineConfig, run_id: str, run_sync: Callable[..., Any] = Runner.run_sync) -> tuple[CandidateOutput | None, AgentTrajectory, AgentTrajectory | None]:
    investigator_input = _input(case)
    bundle, investigator = _run_agent(case, config, run_id, INVESTIGATOR_NAME, INVESTIGATOR_PROMPT_ID, create_investigator, investigator_input, True, run_sync)
    if bundle is None:
        return None, investigator, None
    bundle = with_authoritative_evidence_case_id(case, EvidenceBundleDraft.model_validate(bundle))
    try:
        _validate_bundle(bundle, investigator.tool_calls)
    except ValueError as error:
        investigator.status = "failed"
        investigator.error = f"ValueError: {error}"
        return None, investigator, None
    investigator.output = bundle.model_dump(mode="json")
    resolver_input = json.dumps({"ticket": _input(case), "evidence_bundle": bundle.model_dump(mode="json")}, sort_keys=True)
    draft, resolver = _run_agent(case, config, run_id, RESOLVER_NAME, RESOLVER_PROMPT_ID, create_resolver, resolver_input, False, run_sync)
    if draft is None:
        return None, investigator, resolver
    return with_authoritative_case_id(case, CandidateDraft.model_validate(draft)), investigator, resolver


def run_cases(cases: list[EvaluationCase], config: BaselineConfig, run_id: str, all_cases: bool = False) -> None:
    store = ResolveOpsArtifactStore(run_id)
    store.prepare()
    candidates: dict[str, CandidateOutput] = {}; failures: dict[str, ExecutionFailure] = {}; runtime: dict[str, RuntimeRecord] = {}
    for case in cases:
        candidate, investigator, resolver = run_case(case, config, run_id)
        store.write_trajectory(investigator)
        if resolver: store.write_trajectory(resolver)
        metrics = RuntimeMetrics(latency_ms=(investigator.runtime_metrics.latency_ms or 0) + ((resolver.runtime_metrics.latency_ms or 0) if resolver else 0), retries=(investigator.runtime_metrics.retries or 0) + ((resolver.runtime_metrics.retries or 0) if resolver else 0), tool_call_count=(investigator.runtime_metrics.tool_call_count or 0) + ((resolver.runtime_metrics.tool_call_count or 0) if resolver else 0))
        runtime[case.case_id] = RuntimeRecord(model=config.model, reasoning_effort=config.reasoning_effort, metrics=metrics)
        if candidate is None:
            failed = resolver or investigator
            failures[case.case_id] = ExecutionFailure(case_id=case.case_id, error_type=(failed.error or "ExecutionFailure").split(":", 1)[0], error_message=failed.error or "No candidate produced", infrastructure_retries=metrics.retries or 0)
            if not all_cases: break
        else: candidates[case.case_id] = candidate
    store.write_results(candidates, runtime, failures, ResolveOpsManifest(run_id=run_id, run_kind="official" if all_cases else "development", model=config.model, reasoning_effort=config.reasoning_effort, investigator_prompt_id=INVESTIGATOR_PROMPT_ID, resolver_prompt_id=RESOLVER_PROMPT_ID, case_ids=[case.case_id for case in cases], successful_candidate_count=len(candidates), execution_failure_count=len(failures)))


def main() -> None:
    parser = argparse.ArgumentParser(); group = parser.add_mutually_exclusive_group(required=True); group.add_argument("--case-id"); group.add_argument("--all", action="store_true"); parser.add_argument("--run-id", required=True); args = parser.parse_args()
    if not os.environ.get("OPENAI_API_KEY"): parser.error("OPENAI_API_KEY must be set for a live ResolveOps run.")
    cases = load_cases() if args.all else [select_case(args.case_id)]
    run_cases(cases, BaselineConfig.from_environment(), args.run_id, all_cases=args.all)


if __name__ == "__main__": main()
