"""Evaluator-only truth access. Future agent/runtime code must not import this module."""

import json
from pathlib import Path

from resolveops.evaluation.models import HiddenTruth


def load_hidden_truths() -> list[HiddenTruth]:
    path = Path(__file__).resolve().parent / "data" / "benchmark_truth.json"
    return [HiddenTruth.model_validate(item) for item in json.loads(path.read_text(encoding="utf-8"))]
