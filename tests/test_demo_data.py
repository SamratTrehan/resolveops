from resolveops.app.demo_data import comparison_report, playback, playback_cases


def test_demo_loaders_are_read_only_and_hide_evaluator_fields() -> None:
    assert comparison_report()["runs"][0]["run_id"] == "baseline-official-004"
    assert "CASE-003" in playback_cases()
    stages = playback("resolveops-phase5a-001", "CASE-003")
    assert "investigator-v1" in stages and "verifier-v1" in stages
