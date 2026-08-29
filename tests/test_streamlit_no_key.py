from pathlib import Path

from streamlit.testing.v1 import AppTest

from resolveops.app.demo_data import HISTORICAL_REPLAY, JUDGE_SIMULATION, LIVE_RESOLVEOPS


ROOT = Path(__file__).resolve().parents[1]


def test_no_key_streamlit_modes_are_safe_and_interactive(monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    app = AppTest.from_file(str(ROOT / "streamlit_app.py"))
    app.run()
    assert not app.exception
    assert app.radio[0].value == JUDGE_SIMULATION
    assert any("No new LLM inference" in info.value for info in app.info)

    app.selectbox[0].set_value("Provisioning / approval-required").run()
    app.button[0].click().run()
    assert not app.exception
    assert {button.label for button in app.button} >= {"Approve simulated action", "Reject simulated action"}

    app.radio[0].set_value(HISTORICAL_REPLAY).run()
    assert not app.exception
    app.radio[0].set_value(LIVE_RESOLVEOPS).run()
    assert not app.exception
    assert app.button[0].disabled
    assert any("requires an OpenAI API key" in info.value for info in app.info)
