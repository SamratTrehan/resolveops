import inspect
from pathlib import Path

from resolveops.app import demo_data
from resolveops.app.demo_data import comparison_report, default_case_battle_case


ROOT = Path(__file__).resolve().parents[1]


def test_final_changelog_has_no_scaffolding_and_records_discarded_experiment_and_hot_take() -> None:
    changelog = (ROOT / "IMPROVEMENT_CHANGELOG.md").read_text(encoding="utf-8")
    assert "Future iteration" not in changelog and "Pending" not in changelog
    assert "baseline-official-003" in changelog
    assert "Discarded — unfair output vocabulary" in changelog
    assert "diagnostic and non-comparable" in changelog and "6c25714" in changelog
    assert "## Hot Take" in changelog and "CASE-003" in changelog
    rows = [line for line in changelog.splitlines() if line.startswith("|")]
    assert len(rows) == 7 and all(line.count("|") == 7 for line in rows)


def test_judge_claims_define_strict_success_scope_and_provenance() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    app = (ROOT / "streamlit_app.py").read_text(encoding="utf-8")
    assert "14/15 strict benchmark successes (93.33%)" in readme
    assert "strict benchmark successes ({final.get('vrsr_percent', 0):.2f}%)" in app
    assert "Required evidence-reference coverage" in readme and "100%" in readme
    assert "required evidence-reference coverage" in app
    assert "Verifier approval/rejection and Human Safety Gate approval are not part" in readme
    assert "## Evaluation provenance" in readme and "6c25714" in readme
    assert "does not claim 93% accuracy across general technical support" in readme
    assert "historical dollar cost is unavailable" in readme
    assert "CASE-003 is the final known benchmark failure" in readme
    assert "Final known benchmark failure" in app
    assert "benchmark_truth" not in app
    assert "no forbidden structured claim-ID violation" in readme
    assert "does not semantically scan free-form prose" in readme and "does not semantically scan free-form prose" in app
    assert "py -3.12 -m venv .venv" in readme
    assert "### Expected frozen results" in readme and "73.33% -> 93.33% -> 100.00%" in readme
    assert "Resolution\", \"Status\": \"Verified" not in app
    assert "Resolver revision: before vs after" in app
    assert "Fields changed after verifier feedback" in app
    assert "Architecture, not a stronger model" not in app
    assert "Specialization and verification improved" not in app
    assert "LIVE_RESOLVEOPS" not in app


def test_featured_case_is_fixed_without_outcome_search_and_metrics_are_unchanged() -> None:
    assert default_case_battle_case() == "CASE-006"
    assert "passed" not in inspect.getsource(demo_data.default_case_battle_case)
    runs = comparison_report()["runs"]
    assert [(run["passed_cases"], run["total_cases"], run["vrsr_percent"], run["evidence_coverage"]) for run in runs] == [
        (10, 15, 66.66666666666667, 73.33333333333333),
        (12, 15, 80.0, 93.33333333333333),
        (14, 15, 93.33333333333333, 100.0),
    ]
