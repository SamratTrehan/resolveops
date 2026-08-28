"""Score completed ResolveOps generation artifacts with the shared VRSR scorer."""

import argparse
import json
from pathlib import Path

from resolveops.agents.baseline.records import RuntimeRecord
from resolveops.agents.resolveops.artifacts import ResolveOpsArtifactStore, ResolveOpsManifest
from resolveops.evaluation.benchmark import load_cases
from resolveops.evaluation.hidden_truth import load_hidden_truths
from resolveops.evaluation.models import CandidateOutput, ExecutionFailure
from resolveops.evaluation.scoring import score_benchmark


def score_saved_run(run_id: str, root: Path | None = None) -> None:
    store = ResolveOpsArtifactStore(run_id, root=root)
    paths = {name: store.result_dir / name for name in ("candidates.json", "runtime.json", "manifest.json", "execution_failures.json")}
    if (store.result_dir / "failure.json").exists():
        raise RuntimeError(f"Cannot score incomplete ResolveOps run: {run_id}")
    if any(not path.exists() for path in paths.values()):
        raise FileNotFoundError(f"No completed ResolveOps artifacts found for run: {run_id}")
    manifest = ResolveOpsManifest.model_validate_json(paths["manifest.json"].read_text(encoding="utf-8"))
    cases = load_cases()
    if manifest.status != "completed" or set(manifest.case_ids) != {case.case_id for case in cases}:
        raise RuntimeError(f"Cannot score incomplete ResolveOps run: {run_id}")
    candidates = {key: CandidateOutput.model_validate(value) for key, value in json.loads(paths["candidates.json"].read_text(encoding="utf-8")).items()}
    failures = {key: ExecutionFailure.model_validate(value) for key, value in json.loads(paths["execution_failures.json"].read_text(encoding="utf-8")).items()}
    if set(candidates) | set(failures) != set(manifest.case_ids) or set(candidates) & set(failures):
        raise RuntimeError(f"Cannot score incomplete ResolveOps run: {run_id}")
    runtime = {key: RuntimeRecord.model_validate(value).metrics for key, value in json.loads(paths["runtime.json"].read_text(encoding="utf-8")).items()}
    result = score_benchmark(cases, load_hidden_truths(), candidates, runtime, failures)
    ResolveOpsArtifactStore._write(store.result_dir / "score_summary.json", result.summary.model_dump(mode="json"))
    ResolveOpsArtifactStore._write(store.result_dir / "case_scores.json", [score.model_dump(mode="json") for score in result.case_scores])


def main() -> None:
    parser = argparse.ArgumentParser(description="Score completed ResolveOps artifacts.")
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    score_saved_run(args.run_id)


if __name__ == "__main__":
    main()
