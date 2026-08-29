from pathlib import Path

from streamlit.testing.v1 import AppTest

from resolveops.app.demo_data import HISTORICAL_REPLAY, JUDGE_SIMULATION, LIVE_RESOLVEOPS


ROOT = Path(__file__).resolve().parents[1]


def test_no_key_streamlit_modes_are_safe_and_interactive(monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    app = AppTest.from_file(str(ROOT / "streamlit_app.py"))
    app.run()
    assert not app.exception
    assert app.button[0].label == "Selected"
    assert any("no new llm inference" in info.value.lower() for info in app.info)
    assert "Case Battle" in [tab.label for tab in app.tabs]
    app.selectbox[1].set_value("CASE-006").run()
    assert not app.exception

    app.selectbox[0].set_value("Provisioning / approval-required").run()
    app.button[3].click().run()
    assert not app.exception
    assert {button.label for button in app.button} >= {"Approve simulated action", "Reject simulated action"}
    app.button[4].click().run()
    assert app.session_state["approval_decision"] == "approve"

    app.button[1].click().run()
    assert not app.exception
    assert any("immutable official trajectories" in info.value for info in app.info)
    historical = next(select for select in app.selectbox if select.label == "Case")
    assert any(str(option).startswith("CASE-003") for option in historical.options)
    historical.set_value("CASE-003").run()
    assert not app.exception
    app.button[2].click().run()
    assert not app.exception
    assert app.button[2].disabled
    assert any("requires an OpenAI API key" in info.value for info in app.info)
