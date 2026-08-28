"""Non-overwriting Phase 4 ResolveOps artifacts."""

import json
from pathlib import Path

from pydantic import BaseModel

from resolveops.agents.baseline.artifacts import RUN_ID_PATTERN, repository_root
from resolveops.agents.baseline.records import RuntimeRecord
from resolveops.agents.resolveops.records import AgentTrajectory
from resolveops.evaluation.models import CandidateOutput, ExecutionFailure


class ResolveOpsManifest(BaseModel):
    status: str = "completed"
    run_id: str
    run_kind: str
    model: str
    reasoning_effort: str
    investigator_prompt_id: str
    resolver_prompt_id: str
    case_ids: list[str]
    successful_candidate_count: int = 0
    execution_failure_count: int = 0


class ResolveOpsArtifactStore:
    def __init__(self, run_id: str, root: Path | None = None) -> None:
        if not RUN_ID_PATTERN.fullmatch(run_id):
            raise ValueError("run_id must use lowercase letters, digits, hyphens, or underscores.")
        base = root or repository_root()
        self.result_dir = base / "evaluation" / "results" / "resolveops" / run_id
        self.trajectory_dir = base / "trajectories" / "resolveops" / run_id

    def prepare(self) -> None:
        if self.result_dir.exists() or self.trajectory_dir.exists():
            raise FileExistsError("ResolveOps run already exists.")
        self.result_dir.mkdir(parents=True)
        self.trajectory_dir.mkdir(parents=True)

    def write_trajectory(self, trajectory: AgentTrajectory) -> None:
        self._write(self.trajectory_dir / f"{trajectory.case_id}-{trajectory.prompt_id}.json", trajectory.model_dump(mode="json"))

    def write_results(self, candidates: dict[str, CandidateOutput], runtime: dict[str, RuntimeRecord], failures: dict[str, ExecutionFailure], manifest: ResolveOpsManifest) -> None:
        self._write(self.result_dir / "candidates.json", {key: value.model_dump(mode="json") for key, value in candidates.items()})
        self._write(self.result_dir / "runtime.json", {key: value.model_dump(mode="json") for key, value in runtime.items()})
        self._write(self.result_dir / "execution_failures.json", {key: value.model_dump(mode="json") for key, value in failures.items()})
        self._write(self.result_dir / "manifest.json", manifest.model_dump(mode="json"))

    @staticmethod
    def _write(path: Path, value: object) -> None:
        with path.open("x", encoding="utf-8") as handle:
            json.dump(value, handle, indent=2, sort_keys=True)
            handle.write("\n")
