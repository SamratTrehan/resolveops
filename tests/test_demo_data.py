from resolveops.app.demo_data import chart_data, comparison_rows, comparison_report, display_label, evidence_cards, judge_demo_case, playback, playback_cases, revision_diff, workflow_stages


def test_demo_loaders_are_read_only_and_hide_evaluator_fields() -> None:
    assert comparison_report()["runs"][0]["run_id"] == "baseline-official-004"
    assert "CASE-003" in playback_cases()
    stages = playback("resolveops-phase5a-001", "CASE-003")
    assert "investigator-v1" in stages and "verifier-v1" in stages
    assert display_label("INSUFFICIENT_EVIDENCE") == "Insufficient Evidence"
    assert judge_demo_case() == "CASE-005"
    assert revision_diff(stages)
    assert [name for name, _ in workflow_stages(stages)][:3] == ["investigator-v1", "resolver-v1", "verifier-v1"]
    assert comparison_rows(stages)
    assert chart_data(comparison_report())[0]["stage"] == "Baseline"
    assert evidence_cards(stages["investigator-v1"]["output"])
