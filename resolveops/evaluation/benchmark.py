"""Loading and integrity checks for observable benchmark cases."""

import json
from pathlib import Path

from resolveops.evaluation.models import EvaluationCase, HiddenTruth
from resolveops.tools import SupportEnvironment


def _repository_root() -> Path:
    return Path(__file__).resolve().parents[2]


def load_cases() -> list[EvaluationCase]:
    path = _repository_root() / "data" / "cases" / "benchmark_cases.json"
    return [EvaluationCase.model_validate(item) for item in json.loads(path.read_text(encoding="utf-8"))]


def validate_benchmark_integrity(
    cases: list[EvaluationCase], truths: list[HiddenTruth], environment: SupportEnvironment
) -> None:
    case_ids = {case.case_id for case in cases}
    truth_ids = {truth.case_id for truth in truths}
    if len(case_ids) != len(cases):
        raise ValueError("Observable benchmark case IDs must be unique.")
    if len(truth_ids) != len(truths):
        raise ValueError("Hidden truth case IDs must be unique.")
    if case_ids != truth_ids:
        raise ValueError("Observable cases and hidden truths must have identical case IDs.")
    for case in cases:
        if case.customer_id not in environment.customers:
            raise ValueError(f"Unknown customer in benchmark: {case.customer_id}")
        if case.primary_device_id:
            device = environment.devices.get(case.primary_device_id)
            if not device:
                raise ValueError(f"Unknown device in benchmark: {case.primary_device_id}")
            if environment.accounts[device.account_id].customer_id != case.customer_id:
                raise ValueError(f"Device/customer mismatch in benchmark: {case.case_id}")
