"""Non-overwriting local artifact storage for baseline generation runs."""

import json
import re
from pathlib import Path

from pydantic import BaseModel

from resolveops.agents.baseline.records import BaselineTrajectory, RuntimeRecord
from resolveops.evaluation.models import CandidateOutput


RUN_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")


class RunManifest(BaseModel):
    run_id: str
    run_kind: str
    model: str
    reasoning_effort: str
    agent_name: str
    prompt_id: str
    case_ids: list[str]


def repository_root() -> Path:
    return Path(__file__).resolve().parents[3]


class ArtifactStore:
    def __init__(self, run_id: str, root: Path | None = None) -> None:
        if not RUN_ID_PATTERN.fullmatch(run_id):
            raise ValueError("run_id must use lowercase letters, digits, hyphens, or underscores.")
        base = root or repository_root()
        self.run_id = run_id
        self.result_dir = base / "evaluation" / "results" / "baseline" / run_id
        self.trajectory_dir = base / "trajectories" / "baseline" / run_id

    def prepare(self) -> None:
        if self.result_dir.exists() or self.trajectory_dir.exists():
            raise FileExistsError(f"Baseline run already exists: {self.run_id}")
        self.result_dir.mkdir(parents=True)
        self.trajectory_dir.mkdir(parents=True)

    @staticmethod
    def _write_json(path: Path, value: object) -> None:
        with path.open("x", encoding="utf-8") as handle:
            json.dump(value, handle, indent=2, sort_keys=True)
            handle.write("\n")

    def write_trajectory(self, trajectory: BaselineTrajectory) -> None:
        self._write_json(
            self.trajectory_dir / f"{trajectory.case_id}.json",
            trajectory.model_dump(mode="json"),
        )

    def write_results(
        self,
        candidates: dict[str, CandidateOutput],
        runtime_metadata: dict[str, RuntimeRecord],
        manifest: RunManifest,
    ) -> None:
        self._write_json(
            self.result_dir / "candidates.json",
            {case_id: candidate.model_dump(mode="json") for case_id, candidate in candidates.items()},
        )
        self._write_json(
            self.result_dir / "runtime.json",
            {case_id: record.model_dump(mode="json") for case_id, record in runtime_metadata.items()},
        )
        self._write_json(self.result_dir / "manifest.json", manifest.model_dump(mode="json"))
