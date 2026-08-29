"""ResolveOps judge presentation: recorded simulation, replay, and optional live entrypoint."""

import json
import os

import streamlit as st

from resolveops.agents.resolveops.safety import HumanApproval, safety_gate
from resolveops.app.demo_data import (
    HISTORICAL_REPLAY,
    JUDGE_SIMULATION,
    LIVE_RESOLVEOPS,
    chart_data,
    comparison_report,
    comparison_rows,
    display_label,
    evidence_cards,
    judge_demo_case,
    live_mode_available,
    mode_comparison,
    mode_metadata,
    observable_case,
    playback,
    playback_cases,
    reset_transient_approval,
    simulation_scenarios,
    workflow_steps,
    workflow_stages,
)


def render_safety(answer: dict[str, object], context: str) -> None:
    reset_transient_approval(st.session_state, context)
    decision = st.session_state.get("approval_decision")
    gate = safety_gate(answer["recommended_action_id"], HumanApproval(decision) if decision else None)
    st.caption("SIMULATED — NO REAL SYSTEM CHANGES")
    st.write(f"Safety gate: {gate.approval_status.value.replace('_', ' ')} — {gate.summary}")
    if gate.approval_required:
        left, right = st.columns(2)
        if left.button("Approve simulated action", key=f"approve-{context}"):
            st.session_state["approval_decision"] = HumanApproval.APPROVE.value
            st.rerun()
        if right.button("Reject simulated action", key=f"reject-{context}"):
            st.session_state["approval_decision"] = HumanApproval.REJECT.value
            st.rerun()


def render_workflow_strip(active: str) -> None:
    steps = workflow_steps(active)
    markup = "<span class='workflow-connector'></span>".join(
        f"<div class='workflow-step {'active' if step['active'] else ''}'>{step['label']}</div>" for step in steps
    )
    st.markdown(f"<div class='workflow'>{markup}</div>", unsafe_allow_html=True)


def render_mode_cards() -> str:
    if "selected_mode" not in st.session_state:
        st.session_state["selected_mode"] = JUDGE_SIMULATION
    st.markdown("#### Choose experience")
    columns = st.columns(3)
    for column, item in zip(columns, mode_metadata()):
        selected = st.session_state["selected_mode"] == item["id"]
        with column:
            st.markdown(f"<div class='mode-card {'selected' if selected else ''}'><span class='badge'>{item['badge']}</span><h4>{item['label']}</h4><p>{item['summary']}</p></div>", unsafe_allow_html=True)
            if st.button("Selected" if selected else "Choose", key=f"mode-{item['badge']}", disabled=selected, width="stretch"):
                st.session_state["selected_mode"] = item["id"]
                st.rerun()
    return st.session_state["selected_mode"]


def render_recorded_workflow(case: dict[str, object], stages: dict[str, dict[str, object]], context: str, source: str) -> None:
    st.caption(source)
    st.subheader("Ticket")
    st.write(case["ticket_text"])
    st.caption(f"{case['case_id']} · {case['customer_id']} · {case.get('primary_device_id') or 'No primary device'}")
    investigator = stages.get("investigator-v1", {})
    bundle = investigator.get("output", {})
    st.subheader("Evidence Trail")
    for group, cards in evidence_cards(bundle).items():
        if cards:
            st.markdown(f"**{group.upper()}**")
            for card in cards:
                st.markdown(f"<div class='card'><b>{card['statement']}</b><br><span class='muted'>{card['source_id']} · {card['tool_name']}</span></div>", unsafe_allow_html=True)
    with st.expander("Recorded Investigator tool calls"):
        for attempt in investigator.get("attempts", []):
            for call in attempt.get("tool_calls", []):
                result = call.get("result", {})
                st.markdown(f"**{call.get('tool_name')}** — {result.get('summary', 'Recorded tool result.')}")
    st.caption("OBSERVED FACTS are distinct from Investigator hypotheses.")
    for name, data in workflow_stages(stages):
        with st.expander(name.replace("-", " ").title(), expanded=name == "investigator-v1"):
            output = data.get("output") or {}
            if name == "verifier-v1":
                st.success("✓ APPROVED") if output.get("approved") else st.warning("⚠ REVISION REQUESTED")
                if output.get("issues"):
                    st.caption(" · ".join(display_label(item.get("category")) for item in output["issues"]))
            st.write(output.get("investigation_summary") or output.get("customer_response") or output.get("feedback") or data.get("error") or "Recorded stage.")
            with st.expander("Raw recorded JSON"):
                st.json(output)
    final = stages.get("resolver-revision-v1") or stages.get("resolver-v1")
    if final and final.get("output"):
        answer = final["output"]
        st.subheader("Resolution Packet")
        columns = st.columns(4)
        for column, key in zip(columns, ("root_cause_id", "recommended_action_id", "escalate", "confidence")):
            value = display_label(str(answer.get(key))) if key != "confidence" else answer.get(key)
            column.markdown(f"<div class='card'><b>{key.replace('_', ' ').upper()}</b><br>{value}</div>", unsafe_allow_html=True)
        st.write(answer.get("customer_response"))
        render_safety(answer, context)
        st.download_button("Download recorded Resolution Packet", json.dumps(answer, indent=2), file_name=f"{case['case_id']}-resolution-packet.json", mime="application/json", key=f"download-{context}")
    rows = comparison_rows(stages)
    if any(row["changed"] == "✓" for row in rows):
        st.subheader("Verifier before vs after")
        st.dataframe(rows, hide_index=True, width="stretch")
        st.write("**What the verifier changed:** " + ", ".join(row["label"] for row in rows if row["changed"] == "✓"))
    if case["case_id"] == "CASE-003":
        st.info("Known limitation: shared conservative bias. Independent verification reduces error, but does not guarantee independent judgment.")


st.set_page_config(page_title="ResolveOps", layout="wide")
st.markdown("""<style>.hero{padding:1.5rem;border:1px solid #345;background:#101a27;border-radius:16px}.card{padding:1rem;border:1px solid #345;border-radius:12px;background:#142130}.muted{color:#9ab}.workflow{display:flex;flex-wrap:wrap;gap:.35rem;align-items:center;margin:1rem 0}.workflow-step{border:1px solid #345;background:#101a27;border-radius:999px;padding:.45rem .7rem;color:#9ab;font-size:.82rem}.workflow-step.active{background:#1d3a35;border-color:#4d9b7d;color:#e7fff3;font-weight:600}.workflow-connector{width:1rem;height:1px;background:#345}.mode-card{min-height:8rem;padding:1rem;border:1px solid #345;border-radius:12px;background:#101a27}.mode-card.selected{border-color:#4d9b7d;background:#142b29}.mode-card h4{margin:.45rem 0 .25rem}.mode-card p{margin:0;color:#9ab;font-size:.86rem}.badge{display:inline-block;border:1px solid #4f718d;border-radius:999px;padding:.12rem .4rem;color:#b8d5ee;font-size:.68rem;font-weight:600;letter-spacing:.04em}</style>""", unsafe_allow_html=True)
report = comparison_report()
final = report["runs"][-1] if report else {}
st.markdown(f"<div class='hero'><h1>ResolveOps</h1><h3>Evidence-grounded support. Verified before action.</h3><p>Multi-agent technical support that investigates evidence, verifies its own resolution, and requires human approval before consequential simulated actions.</p><b>{final.get('vrsr_percent', 0):.1f}% Verified Resolution Success</b> &nbsp; <b>{final.get('evidence_coverage', 0):.0f}% Evidence Coverage</b> &nbsp; <b>Human Safety Gate</b></div>", unsafe_allow_html=True)
st.caption("Synthetic demo only — never enter real customer data, credentials, or private information.")

api_key = os.environ.get("OPENAI_API_KEY")
mode = render_mode_cards()
reset_transient_approval(st.session_state, f"mode:{mode}")
render_workflow_strip("Resolution" if mode != JUDGE_SIMULATION or st.session_state.get("simulation_started") else "Ticket")
if mode == JUDGE_SIMULATION:
    st.info("Explore the full ResolveOps workflow using recorded agent outputs and synthetic support scenarios. No API key required; no new LLM inference occurs.")
elif mode == HISTORICAL_REPLAY:
    st.info("Inspect immutable official trajectories directly. This read-only view uses no API key and performs no new LLM inference.")
else:
    st.info("Run fresh inference only with a configured server-side OpenAI API key.")

st.dataframe(mode_comparison(), hide_index=True, width="stretch")
experience, improvement = st.tabs(["Run a scenario", "Measured Improvement"])

with experience:
    if mode == JUDGE_SIMULATION:
        scenarios = simulation_scenarios()
        labels = {scenario["label"]: scenario for scenario in scenarios}
        selected = st.selectbox("Scenario", labels)
        scenario = labels[selected]
        case = scenario["case"]
        run_context = f"simulation:{case['case_id']}"
        if st.session_state.get("simulation_case") != case["case_id"]:
            st.session_state.pop("simulation_started", None)
            st.session_state["simulation_case"] = case["case_id"]
            reset_transient_approval(st.session_state, run_context)
        st.write(case["ticket_text"])
        if st.button("Run ResolveOps simulation", type="primary"):
            st.session_state["simulation_started"] = True
        if st.session_state.get("simulation_started"):
            render_recorded_workflow(case, playback("resolveops-phase5a-001", case["case_id"]), run_context, "Interactive Judge Simulation — recorded agent outputs, zero API calls")
        else:
            st.caption("Choose a synthetic ticket and run the recorded simulation to inspect its full workflow.")
    elif mode == HISTORICAL_REPLAY:
        paths = {"Judge Demo — revised success": judge_demo_case(), "Explore known limitation": "CASE-003"}
        selected = st.radio("Historical trajectory", paths, horizontal=True)
        case_id = paths[selected]
        case = observable_case(case_id)
        render_recorded_workflow(case, playback("resolveops-phase5a-001", case_id), f"replay:{case_id}", "Historical Replay — immutable recorded trajectory, zero API calls")
    else:
        st.write("Use this mode only for genuinely fresh, API-backed inference. The Streamlit demo does not request credentials or auto-run a model.")
        st.button("Run Live ResolveOps", disabled=not live_mode_available(api_key), type="primary")
        if not live_mode_available(api_key):
            st.info("Live ResolveOps requires an OpenAI API key. Use Interactive Judge Simulation for the full no-key experience.")
        else:
            st.caption("Use the documented CLI to create a persisted live run with a new explicit run ID.")

with improvement:
    if not report:
        st.warning("Comparison report is unavailable. Run `python -m resolveops.evaluation.report_experiments`.")
    else:
        runs = report["runs"]
        columns = st.columns(3)
        for column, run in zip(columns, runs):
            column.metric(run["architecture"], f"{run['vrsr_percent']:.2f}%", f"Evidence {run['evidence_coverage']:.2f}%")
        st.vega_lite_chart({"data": {"values": chart_data(report)}, "mark": "bar", "encoding": {"x": {"field": "stage", "type": "nominal", "axis": {"labelAngle": 0}}, "y": {"field": "vrsr", "type": "quantitative", "scale": {"domain": [0, 100]}}, "tooltip": [{"field": "vrsr", "type": "quantitative"}]}}, width="stretch")
        st.metric("Baseline → final VRSR", f"+{runs[-1]['vrsr_percent']-runs[0]['vrsr_percent']:.1f} pp")
        st.metric("Phase 4 → verifier VRSR", f"+{runs[-1]['vrsr_percent']-runs[1]['vrsr_percent']:.1f} pp")
        st.caption("Reliability came at a cost: latency and recorded tokens increased. Additional agents must earn their cost.")
