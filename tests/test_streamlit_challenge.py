from pathlib import Path
import re
from types import SimpleNamespace

from streamlit.testing.v1 import AppTest

from resolveops.agents.resolveops.schemas import EvidenceBundleDraft, ObservedFact, VerificationDecision
from resolveops.app import judge_challenge
from resolveops.evaluation.models import CandidateDraft, EvidenceReference
from resolveops.tools.simulator import default_environment


ROOT = Path(__file__).resolve().parents[1]


def _fake_sdk_run(agent: object, user_input: str, **kwargs: object) -> object:
    customer_id = re.search(r"CUS-\d{3}", user_input).group()
    reference = EvidenceReference(tool_name="get_account_status", source_id=customer_id)
    if agent.name == "ResolveOps Investigator":
        result = default_environment().get_account_status(customer_id)
        kwargs["context"].record("get_account_status", {"customer_id": customer_id}, result)
        output = EvidenceBundleDraft(
            ticket_summary="Synthetic ticket.",
            observed_facts=[ObservedFact(statement=result.summary, evidence_references=[reference])],
            evidence_references=[reference],
            investigation_summary="Synthetic evidence collected.",
        )
    elif agent.name == "ResolveOps Verifier":
        output = VerificationDecision(approved=True, feedback="Approved from supplied evidence.")
    else:
        output = CandidateDraft(
            root_cause_id="regional_outage",
            confidence=0.8,
            recommended_action_id="communicate_outage_status",
            escalate=False,
            evidence_references=[reference],
            customer_response="Synthetic response.",
            internal_notes="Synthetic notes.",
        )
    return SimpleNamespace(final_output=output, context_wrapper=None)


def test_streamlit_fresh_mode_runs_once_with_mocked_openai_boundary(monkeypatch) -> None:
    secret = "test-server-secret"
    monkeypatch.setenv("OPENAI_API_KEY", secret)
    monkeypatch.setattr(judge_challenge, "_sdk_run_sync", lambda api_key: _fake_sdk_run)
    app = AppTest.from_file(str(ROOT / "streamlit_app.py"))
    app.run()
    next(button for button in app.button if button.key == "mode-FRESH").click().run()
    assert not app.exception
    run_button = next(button for button in app.button if button.key == "run-fresh-resolveops")
    assert not run_button.disabled
    run_button.click().run()
    assert not app.exception
    assert app.session_state["judge_challenge_consumed"] is True
    assert "judge_challenge_result" in app.session_state
    rendered = " ".join(
        [item.value for item in app.success]
        + [item.value for item in app.markdown]
        + [item.value for item in app.caption]
    )
    assert "Generated during this session" in rendered
    assert "not included in official benchmark metrics" in rendered
    assert next(button for button in app.button if button.key == "run-fresh-resolveops").disabled
    assert secret not in repr(app.session_state)
