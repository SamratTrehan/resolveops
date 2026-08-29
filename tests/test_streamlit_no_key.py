from pathlib import Path

from streamlit.testing.v1 import AppTest

from resolveops.app.synthetic_sandbox import read_sandbox_state

ROOT = Path(__file__).resolve().parents[1]


def _button(app: AppTest, key: str):
    return next(button for button in app.button if button.key == key)


def _selectbox(app: AppTest, label: str):
    return next(selectbox for selectbox in app.selectbox if selectbox.label == label)


def test_no_key_streamlit_modes_are_safe_and_interactive(monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    app = AppTest.from_file(str(ROOT / "streamlit_app.py"))
    app.run()
    assert not app.exception
    assert app.button[0].label == "Selected"
    assert any("no new llm inference" in info.value.lower() for info in app.info)
    assert "Case Battle" in [tab.label for tab in app.tabs]
    _selectbox(app, "Comparison case").set_value("CASE-006").run()
    assert not app.exception

    _selectbox(app, "Scenario").set_value("Provisioning / approval-required").run()
    next(button for button in app.button if button.label == "Run ResolveOps simulation").click().run()
    assert not app.exception
    assert {button.label for button in app.button} >= {"Approve simulated action", "Reject simulated action"}
    assert read_sandbox_state(app.session_state, "simulation:CASE-002", "CUS-003", "DEV-004").provisioning_status == "awaiting_gateway_activation"
    next(button for button in app.button if button.label == "Approve simulated action").click().run()
    assert app.session_state["approval_decision"] == "approve"
    assert read_sandbox_state(app.session_state, "simulation:CASE-002", "CUS-003", "DEV-004").provisioning_status == "complete"

    _button(app, "mode-FRESH").click().run()
    assert not app.exception
    assert any("temporarily unavailable" in info.value.lower() for info in app.info)
    assert _button(app, "run-fresh-resolveops").disabled
    assert "judge_challenge_consumed" not in app.session_state

    _button(app, "mode-RECORDED").click().run()
    assert not app.exception
    assert any("immutable official trajectories" in info.value for info in app.info)
    historical = _selectbox(app, "Case")
    assert any(str(option).startswith("CASE-003") for option in historical.options)
    historical.set_value("CASE-003").run()
    assert not app.exception
    _button(app, "mode-LIVE").click().run()
    assert not app.exception
    assert next(button for button in app.button if button.label == "Run Live ResolveOps").disabled
    assert any("requires an OpenAI API key" in info.value for info in app.info)
