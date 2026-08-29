"""ResolveOps judge presentation: recorded views and bounded fresh inference."""

import json
import os

import streamlit as st

from resolveops.agents.resolveops.safety import HumanApproval, safety_gate
from resolveops.app.demo_data import (
    HISTORICAL_REPLAY,
    JUDGE_CHALLENGE,
    JUDGE_SIMULATION,
    LIVE_RESOLVEOPS,
    chart_data,
    case_battle,
    case_battle_case_ids,
    case_battle_divergences,
    comparison_report,
    comparison_rows,
    display_label,
    default_case_battle_case,
    evidence_coverage_data,
    evidence_cards,
    judge_demo_case,
    live_mode_available,
    mode_comparison,
    mode_metadata,
    observable_case,
    playback,
    playback_cases,
    reset_transient_approval,
    reset_approval_for_mode,
    simulation_scenarios,
    workflow_steps,
    workflow_stages,
)
from resolveops.app.judge_challenge import (
    ChallengeAllowanceUsed,
    ChallengeExecutionError,
    FreshRunResult,
    FRESH_ERROR_KEY,
    FRESH_RESULT_KEY,
    FRESH_RUN_ALLOWANCE,
    challenge_templates,
    configured_server_key,
    fresh_allowance_available,
    resolution_packet_export,
    run_challenge_once,
    stage_mapping,
)


def render_safety(answer: dict[str, object], context: str) -> None:
    reset_transient_approval(st.session_state, context)
    decision = st.session_state.get("approval_decision")
    gate = safety_gate(answer["recommended_action_id"], HumanApproval(decision) if decision else None)
    st.caption("SIMULATED — NO REAL SYSTEM CHANGES")
    if gate.approval_required:
        st.write("**Approval required**")
        st.write(f"Status: {display_label(gate.approval_status.value)}")
        if decision:
            st.write(f"Human decision: {display_label(decision)}")
            st.write(f"Synthetic execution: {'Completed' if decision == HumanApproval.APPROVE.value else 'Blocked'}")
            if decision == HumanApproval.REJECT.value:
                st.write("No action executed.")
        else:
            st.caption(gate.summary)
        left, right = st.columns(2)
        if left.button("Approve simulated action", key=f"approve-{context}"):
            st.session_state["approval_decision"] = HumanApproval.APPROVE.value
            st.rerun()
        if right.button("Reject simulated action", key=f"reject-{context}"):
            st.session_state["approval_decision"] = HumanApproval.REJECT.value
            st.rerun()
    else:
        st.write(f"Safety gate: {display_label(gate.approval_status.value)} — {gate.summary}")


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
    columns = st.columns(len(mode_metadata()))
    for column, item in zip(columns, mode_metadata()):
        selected = st.session_state["selected_mode"] == item["id"]
        with column:
            st.markdown(f"<div class='mode-card {'selected' if selected else ''}'><span class='badge'>{item['badge']}</span><h4>{item['label']}</h4><p>{item['summary']}</p></div>", unsafe_allow_html=True)
            if st.button("Selected" if selected else "Choose", key=f"mode-{item['badge']}", disabled=selected, width="stretch"):
                st.session_state["selected_mode"] = item["id"]
                st.rerun()
    return st.session_state["selected_mode"]


def display_value(value: object) -> str:
    if value is None:
        return "Not recorded"
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, float):
        return f"{value:.2f}"
    return str(value)


def render_battle_side(title: str, data: dict[str, object], final: bool = False) -> None:
    candidate, runtime, score = data["candidate"], data["runtime"], data["score"]
    st.markdown(f"### {title}")
    st.caption("Evidence + verification pipeline" if final else "One general tool-using agent")
    st.markdown(f"<div class='card'><b>Architecture</b><br>{data['architecture']}</div>", unsafe_allow_html=True)
    rows = [
        {"Field": "Tool calls", "Value": display_value(runtime.get("tool_call_count"))},
        {"Field": "Evidence references", "Value": display_value(len(candidate["evidence_references"]))},
        {"Field": "Diagnosis / root cause", "Value": display_label(candidate["root_cause_id"])},
        {"Field": "Recommended action", "Value": display_label(candidate["recommended_action_id"])},
        {"Field": "Escalation", "Value": display_value(candidate["escalate"])},
        {"Field": "Confidence", "Value": display_value(candidate["confidence"])},
        {"Field": "Execution failure", "Value": display_value(score["execution_failure"])},
        {"Field": "Infrastructure retries", "Value": display_value(runtime.get("retries"))},
        {"Field": "Latency", "Value": f"{runtime['latency_ms']:.0f} ms" if runtime.get("latency_ms") is not None else "Not recorded"},
        {"Field": "Recorded tokens", "Value": display_value(runtime.get("token_usage"))},
    ]
    if final:
        verifier = data["verifier"]
        rows += [
            {"Field": "Investigator evidence", "Value": display_value(data["investigator_evidence_count"])},
            {"Field": "Verifier decision", "Value": "Approved" if verifier["approved"] else "Revision requested"},
            {"Field": "Revision occurred", "Value": display_value(verifier["revision_occurred"])},
        ]
    st.dataframe(rows, hide_index=True, width="stretch")
    outcomes = [
        {"Measure": "Resolution", "Status": "Verified" if score["passed"] else "Did not pass"},
        {"Measure": "Diagnosis", "Status": "Pass" if score["diagnosis_correct"] else "Did not pass"},
        {"Measure": "Action", "Status": "Pass" if score["action_correct"] else "Did not pass"},
        {"Measure": "Escalation", "Status": "Pass" if score["escalation_correct"] else "Did not pass"},
        {"Measure": "Required evidence references", "Status": "Pass" if score["evidence_coverage"] else "Did not pass"},
    ]
    st.caption("Official benchmark outcome")
    st.dataframe(outcomes, hide_index=True, width="stretch")


def render_case_battle() -> None:
    case_ids = case_battle_case_ids()
    default = default_case_battle_case()
    selected = st.selectbox("Comparison case", case_ids, index=case_ids.index(default), key="battle-case")
    if selected == default:
        st.caption("Featured comparison: CASE-006 clearly demonstrates an evidence-reference correction; all comparable cases are selectable.")
    battle = case_battle(selected)
    case = battle["case"]
    st.caption("SAME SUPPORT TICKET")
    st.subheader(case["ticket_text"])
    st.caption(f"{case['case_id']} · {case['customer_id']} · {case.get('primary_device_id') or 'No primary device'}")
    baseline_column, resolveops_column = st.columns(2)
    with baseline_column:
        render_battle_side("BASELINE", battle["baseline"])
    with resolveops_column:
        render_battle_side("RESOLVEOPS", battle["resolveops"], final=True)

    st.subheader("Where the architectures diverged")
    for message in case_battle_divergences(battle):
        st.write(message)

    st.subheader("Evidence used in the final answer")
    baseline_refs = {(item["tool_name"], item["source_id"]) for item in battle["baseline"]["candidate"]["evidence_references"]}
    resolveops_refs = {(item["tool_name"], item["source_id"]) for item in battle["resolveops"]["candidate"]["evidence_references"]}
    baseline_evidence, resolveops_evidence = st.columns(2)
    for column, title, refs in ((baseline_evidence, "BASELINE", baseline_refs), (resolveops_evidence, "RESOLVEOPS", resolveops_refs)):
        with column:
            st.markdown(f"**{title}**")
            rows = [row for row in battle["evidence"] if (row["tool_name"], row["source_id"]) in refs]
            st.dataframe(rows, hide_index=True, width="stretch")

    verifier = battle["resolveops"]["verifier"]
    st.subheader("Verifier intervention")
    if verifier["revision_occurred"]:
        st.write("Verifier requested a bounded Resolver revision.")
        if verifier["issue_categories"]:
            st.caption("Issue categories: " + " · ".join(display_label(item) for item in verifier["issue_categories"]))
        st.caption("Fields changed: " + (", ".join(verifier["changed_fields"]) or "None recorded"))
        st.caption(f"Evidence references: {verifier['before_evidence_count']} → {verifier['after_evidence_count']} · Confidence: {display_value(verifier['before_confidence'])} → {display_value(verifier['after_confidence'])}")
    else:
        st.write("Verifier approved the Resolver output without revision.")
    with st.expander("Recorded candidate packets"):
        st.json({"baseline": battle["baseline"]["candidate"], "resolveops": battle["resolveops"]["candidate"]})


def render_recorded_workflow(
    case: dict[str, object],
    stages: dict[str, dict[str, object]],
    context: str,
    source: str,
    final_answer: dict[str, object] | None = None,
    export_payload: dict[str, object] | None = None,
    download_label: str = "Download recorded Resolution Packet",
) -> None:
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
        answer = final_answer or final["output"]
        st.subheader("Resolution Packet")
        columns = st.columns(4)
        for column, key in zip(columns, ("root_cause_id", "recommended_action_id", "escalate", "confidence")):
            value = display_label(str(answer.get(key))) if key != "confidence" else answer.get(key)
            column.markdown(f"<div class='card'><b>{key.replace('_', ' ').upper()}</b><br>{value}</div>", unsafe_allow_html=True)
        st.write(answer.get("customer_response"))
        render_safety(answer, context)
        st.download_button(download_label, json.dumps(export_payload or answer, indent=2), file_name=f"{case['case_id']}-resolution-packet.json", mime="application/json", key=f"download-{context}")
    rows = comparison_rows(stages)
    if any(row["changed"] == "✓" for row in rows):
        st.subheader("Verifier before vs after")
        st.dataframe(rows, hide_index=True, width="stretch")
        st.write("**What the verifier changed:** " + ", ".join(row["label"] for row in rows if row["changed"] == "✓"))
    if case["case_id"] == "CASE-003":
        st.info("Known limitation: shared conservative bias. Independent verification reduces error, but does not guarantee independent judgment.")


def render_fresh_result(result: FreshRunResult) -> None:
    stages = stage_mapping(result)
    investigator = stages.get("investigator-v1", {})
    bundle = investigator.get("output", {})
    calls = investigator.get("tool_calls", [])
    resolver = stages.get("resolver-v1", {}).get("output", {})
    verifier = stages.get("verifier-v1", {}).get("output", {})
    revision_occurred = "resolver-revision-v1" in stages
    st.success("Fresh demonstration run — not included in official benchmark metrics.")
    st.markdown("**Generated during this session**")
    st.caption(f"Run ID: {result.run_id} · Started: {result.started_at.isoformat()} · {result.model} · reasoning effort: {result.reasoning_effort}")
    st.caption("Investigator → Resolver → Verifier → Conditional Revision → Safety Gate → Resolution")
    st.markdown("**Investigator activity**")
    st.caption(f"{len(calls)} tool calls · {len(bundle.get('evidence_references', []))} collected evidence references")
    if calls:
        st.dataframe(
            [
                {
                    "Tool": call.get("tool_name"),
                    "Source IDs": ", ".join(call.get("result", {}).get("source_ids", [])) or "None",
                    "Observed result": call.get("result", {}).get("summary", "Synthetic tool result."),
                }
                for call in calls
            ],
            hide_index=True,
            width="stretch",
        )
    st.markdown("**Resolver proposal**")
    st.dataframe(
        [
            {"Field": "Root cause", "Value": display_label(resolver.get("root_cause_id"))},
            {"Field": "Recommended action", "Value": display_label(resolver.get("recommended_action_id"))},
            {"Field": "Escalate", "Value": display_value(resolver.get("escalate"))},
            {"Field": "Confidence", "Value": display_value(resolver.get("confidence"))},
            {"Field": "Evidence references", "Value": display_value(len(resolver.get("evidence_references", [])))},
        ],
        hide_index=True,
        width="stretch",
    )
    if verifier.get("approved"):
        st.success("Verifier approved without revision.")
    else:
        st.warning("Verifier requested one bounded Resolver revision." if revision_occurred else "Verifier requested revision; the fresh run did not produce one.")
        if verifier.get("issues"):
            st.caption("Issue categories: " + " · ".join(display_label(item.get("category")) for item in verifier["issues"]))
        st.caption(verifier.get("feedback", ""))
    render_recorded_workflow(
        result.case.model_dump(mode="json"),
        stages,
        f"fresh:{result.run_id}",
        f"Fresh demonstration run — generated during this session at {result.started_at.isoformat()}",
        final_answer=result.candidate.model_dump(mode="json"),
        export_payload=resolution_packet_export(result),
        download_label="Download fresh Resolution Packet",
    )
    st.markdown("**Internal notes**")
    st.write(result.candidate.internal_notes)
    st.markdown("**Final evidence references**")
    st.dataframe(
        [item.model_dump(mode="json") for item in result.candidate.evidence_references],
        hide_index=True,
        width="stretch",
    )


st.set_page_config(page_title="ResolveOps", layout="wide")
st.markdown("""<style>.hero{padding:1.5rem;border:1px solid #345;background:#101a27;border-radius:16px}.card{padding:1rem;border:1px solid #345;border-radius:12px;background:#142130}.muted{color:#9ab}.workflow{display:flex;flex-wrap:wrap;gap:.35rem;align-items:center;margin:1rem 0}.workflow-step{border:1px solid #345;background:#101a27;border-radius:999px;padding:.45rem .7rem;color:#9ab;font-size:.82rem}.workflow-step.active{background:#1d3a35;border-color:#4d9b7d;color:#e7fff3;font-weight:600}.workflow-connector{width:1rem;height:1px;background:#345}.mode-card{min-height:8rem;padding:1rem;border:1px solid #345;border-radius:12px;background:#101a27}.mode-card.selected{border-color:#4d9b7d;background:#142b29}.mode-card h4{margin:.45rem 0 .25rem}.mode-card p{margin:0;color:#9ab;font-size:.86rem}.badge{display:inline-block;border:1px solid #4f718d;border-radius:999px;padding:.12rem .4rem;color:#b8d5ee;font-size:.68rem;font-weight:600;letter-spacing:.04em}.improvement-heading{margin:.25rem 0}.metric-note{margin:.35rem 0 .65rem;color:#c4d5e5;font-size:.92rem}</style>""", unsafe_allow_html=True)
report = comparison_report()
final = report["runs"][-1] if report else {}
st.markdown(f"<div class='hero'><h1>ResolveOps</h1><h3>Evidence-grounded support with a separate verification stage.</h3><p>Multi-agent technical support that investigates synthetic evidence, verifies its proposed resolution, and requires human approval before simulated state-changing actions.</p><b>{final.get('passed_cases', 0)}/{final.get('total_cases', 0)} strict benchmark successes</b> &nbsp; <b>{final.get('evidence_coverage', 0):.0f}% required evidence-reference coverage</b> &nbsp; <b>Human approval before simulated state-changing actions</b></div>", unsafe_allow_html=True)
st.caption("Synthetic demo only — never enter real customer data, credentials, or private information.")

api_key = configured_server_key(st.secrets, os.environ)
mode = render_mode_cards()
reset_approval_for_mode(st.session_state, mode)
workflow_complete = (
    mode == HISTORICAL_REPLAY
    or mode == LIVE_RESOLVEOPS
    or (mode == JUDGE_SIMULATION and st.session_state.get("simulation_started"))
    or (mode == JUDGE_CHALLENGE and st.session_state.get(FRESH_RESULT_KEY))
)
render_workflow_strip("Resolution" if workflow_complete else "Ticket")
if mode == JUDGE_SIMULATION:
    st.info("Explore the full ResolveOps workflow using recorded agent outputs and synthetic support scenarios. No API key required; no new LLM inference occurs.")
elif mode == JUDGE_CHALLENGE:
    st.info("Run one fresh ResolveOps execution on a judge-controlled synthetic ticket. This path performs new model inference. The input is restricted to the synthetic support world. Frozen benchmark results are not modified.")
elif mode == HISTORICAL_REPLAY:
    st.info("Inspect immutable official trajectories directly. This read-only view uses no API key and performs no new LLM inference.")
else:
    st.info("Run fresh inference only with a configured server-side OpenAI API key.")

st.dataframe(mode_comparison(), hide_index=True, width="stretch")
experience, battle_tab, improvement = st.tabs(["Run a scenario", "Case Battle", "Measured Improvement"])

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
    elif mode == JUDGE_CHALLENGE:
        templates = challenge_templates()
        template_ids = [case.case_id for case in templates]
        template_id = st.selectbox("Synthetic case template", template_ids, format_func=lambda value: f"{value} — observable synthetic ticket", key="fresh-template")
        template = next(case for case in templates if case.case_id == template_id)
        identity_columns = st.columns(2)
        identity_columns[0].text_input("Customer", value=template.customer_id, disabled=True, key=f"fresh-customer-{template_id}")
        identity_columns[1].text_input("Primary device", value=template.primary_device_id or "None", disabled=True, key=f"fresh-device-{template_id}")
        ticket_text = st.text_area("Ticket text", value=template.ticket_text, max_chars=2_000, key=f"fresh-ticket-{template_id}")
        st.caption("You can rewrite the symptom description. Customer/device state remains in the synthetic world.")
        st.caption(f"Fresh run allowance: {FRESH_RUN_ALLOWANCE} per session. This is a session-level judge budget, not a security-grade global rate limit.")
        if not api_key:
            st.info("Fresh inference is temporarily unavailable. The recorded Judge Simulation and Historical Replay remain fully available.")
        elif not fresh_allowance_available(st.session_state):
            st.info("Fresh run used for this session. Use recorded replay to inspect additional cases.")
        run_disabled = not api_key or not fresh_allowance_available(st.session_state)
        if st.button("Run fresh ResolveOps", type="primary", disabled=run_disabled, key="run-fresh-resolveops"):
            with st.spinner("Running fresh ResolveOps workflow..."):
                try:
                    run_challenge_once(st.session_state, template_id, ticket_text, api_key)
                except (ChallengeAllowanceUsed, ChallengeExecutionError):
                    pass
            st.rerun()
        if st.session_state.get(FRESH_ERROR_KEY):
            st.error("Fresh inference did not complete. No benchmark artifacts were modified. Recorded judge modes remain available.")
        if st.session_state.get(FRESH_RESULT_KEY):
            render_fresh_result(FreshRunResult.model_validate(st.session_state[FRESH_RESULT_KEY]))
        else:
            st.caption("Fresh demonstration run — not included in official benchmark metrics.")
    elif mode == HISTORICAL_REPLAY:
        cases = playback_cases()
        case_id = st.selectbox("Case", cases, index=cases.index(judge_demo_case()), format_func=lambda value: f"{value} — Recorded trajectory", key="historical-case")
        case = observable_case(case_id)
        render_recorded_workflow(case, playback("resolveops-phase5a-001", case_id), f"replay:{case_id}", "Historical Replay — immutable recorded trajectory, zero API calls")
    else:
        st.write("Use this mode only for genuinely fresh, API-backed inference. The Streamlit demo does not request credentials or auto-run a model.")
        st.button("Run Live ResolveOps", disabled=not live_mode_available(api_key), type="primary")
        if not live_mode_available(api_key):
            st.info("Live ResolveOps requires an OpenAI API key. Use Interactive Judge Simulation for the full no-key experience.")
        else:
            st.caption("Use the documented CLI to create a persisted live run with a new explicit run ID.")

with battle_tab:
    st.caption("Frozen fair baseline versus final ResolveOps on the same observable support ticket. Zero API calls.")
    report_runs = report["runs"] if report else []
    if len(report_runs) >= 3:
        baseline_run, final_run = report_runs[0], report_runs[-1]
        st.markdown("**Architecture, not a stronger model.**")
        st.caption(f"Both frozen runs used {baseline_run['model']} with {baseline_run['reasoning_effort']} reasoning effort. The measured difference came from evidence specialization, a separate verification stage, and bounded correction.")
        st.caption("Same 15 cases · same tools and synthetic world · same scorer.")
        st.caption(f"{baseline_run['vrsr_percent']:.2f}% → {final_run['vrsr_percent']:.2f}% strict benchmark success · {baseline_run['evidence_coverage']:.2f}% → {final_run['evidence_coverage']:.2f}% required evidence-reference coverage. Recorded latency and token use increased with the final architecture.")
    render_case_battle()

with improvement:
    if not report:
        st.warning("Comparison report is unavailable. Run `python -m resolveops.evaluation.report_experiments`.")
    else:
        runs = report["runs"]
        improvement_data = chart_data(report)
        st.markdown("<h3 class='improvement-heading'>Strict Benchmark Success (VRSR)</h3>", unsafe_allow_html=True)
        st.caption("A strict pass requires an accepted diagnosis or abstention, accepted action, correct escalation, required evidence-reference coverage, and no forbidden critical claim. Verifier decisions and Human Safety Gate approval are audited separately and do not affect this deterministic score.")
        columns = st.columns(3)
        for column, item in zip(columns, improvement_data):
            column.metric(item["stage"], f"{item['vrsr']:.2f}%")
        st.vega_lite_chart({"height": 180, "data": {"values": improvement_data}, "mark": "bar", "encoding": {"x": {"field": "stage", "type": "nominal", "axis": {"labelAngle": 0}}, "y": {"field": "vrsr", "type": "quantitative", "scale": {"domain": [0, 100]}}, "tooltip": [{"field": "vrsr", "type": "quantitative"}]}}, width="stretch")
        st.markdown(f"<p class='metric-note'>VRSR improved by {runs[-1]['vrsr_percent']-runs[0]['vrsr_percent']:.1f} percentage points from baseline to final.</p>", unsafe_allow_html=True)
        st.markdown("<h3 class='improvement-heading'>Required Evidence-Reference Coverage</h3>", unsafe_allow_html=True)
        evidence_data = evidence_coverage_data(report)
        st.vega_lite_chart({"height": 180, "data": {"values": evidence_data}, "mark": "bar", "encoding": {"x": {"field": "stage", "type": "nominal", "axis": {"labelAngle": 0}}, "y": {"field": "evidence", "type": "quantitative", "scale": {"domain": [0, 100]}}, "tooltip": [{"field": "evidence", "type": "quantitative"}]}}, width="stretch")
        coverage_columns = st.columns(3)
        for column, item in zip(coverage_columns, evidence_data):
            column.metric(item["stage"], f"{item['evidence']:.2f}%")
        st.markdown(f"<p class='metric-note'>Specialization and verification improved required evidence-reference coverage from {runs[0]['evidence_coverage']:.2f}% to {runs[-1]['evidence_coverage']:.2f}%.</p>", unsafe_allow_html=True)
        st.markdown("<p class='metric-note'>Reliability came at a cost: latency and recorded tokens increased. Additional agents must earn their cost.</p>", unsafe_allow_html=True)
