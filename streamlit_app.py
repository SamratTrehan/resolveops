"""Streamlit judge demo; historical playback is read-only."""

import os

import streamlit as st

from resolveops.app.demo_data import chart_data, comparison_report, comparison_rows, display_label, evidence_cards, judge_demo_case, playback, playback_cases, workflow_stages
from resolveops.agents.resolveops.safety import HumanApproval, safety_gate


st.set_page_config(page_title="ResolveOps", layout="wide")
st.markdown("""<style>.hero{padding:1.5rem;border:1px solid #345;background:#101a27;border-radius:16px}.card{padding:1rem;border:1px solid #345;border-radius:12px;background:#142130}.muted{color:#9ab}</style>""", unsafe_allow_html=True)
report = comparison_report(); final = report["runs"][-1] if report else {}
st.markdown(f"<div class='hero'><h1>ResolveOps</h1><h3>Evidence-grounded support. Verified before action.</h3><p>Multi-agent technical support that investigates evidence, verifies its own resolution, and requires human approval before consequential simulated actions.</p><b>✓ {final.get('vrsr_percent', 0):.1f}% Verified Resolution Success</b> &nbsp; <b>✓ {final.get('evidence_coverage', 0):.0f}% Evidence Coverage</b> &nbsp; <b>👤 Human-in-the-loop Safety</b></div>", unsafe_allow_html=True)
st.caption("Synthetic demo only — never enter real customer data, credentials, or private information.")
st.markdown("🎫 **Ticket** → 🔎 **Investigator** → 🧠 **Resolver** → 🛡️ **Verifier** → 🔁 **Conditional revision** → 👤 **Safety gate** → 📦 **Resolution**")

overview, improvement, recorded = st.tabs(["Resolve a ticket", "Measured Improvement", "▶ Judge Demo"])
with overview:
    st.write("Technical support requires correlating account, device, outage, diagnostics, ticket-history, and KB evidence without making unsupported claims.")
    st.markdown("`Ticket → Investigator → Resolver → Verifier → optional revision → Safety Gate → Resolution Packet`")
    curated = {"Outage": ("All devices lost internet; gateway lights appear normal.", "CUS-002", "DEV-003"), "Provisioning / approval": ("Replacement gateway setup never completes.", "CUS-003", "DEV-004"), "Camera": ("Porch camera stopped reporting after a power interruption.", "CUS-004", "DEV-007"), "Insufficient evidence": ("Brief evening drops, but no times or affected devices were captured.", "CUS-001", "DEV-001")}
    choice = st.selectbox("Synthetic demo ticket", list(curated) + ["Custom synthetic input"])
    default = curated.get(choice, ("", "", ""))
    ticket = st.text_area("Ticket", default[0]); customer = st.text_input("Synthetic customer ID", default[1]); device = st.text_input("Optional synthetic device ID", default[2])
    st.warning("Run ResolveOps may consume OpenAI API tokens.")
    if st.button("Run ResolveOps", type="primary"):
        if not os.environ.get("OPENAI_API_KEY"):
            st.error("OPENAI_API_KEY is required for live execution. Use Historical playback for a no-API demo.")
        else:
            st.info("Live execution is intentionally not auto-run on widget changes. Use the CLI for a persisted run.")
with improvement:
    if not report:
        st.warning("Comparison report is unavailable. Run `python -m resolveops.evaluation.report_experiments`.")
    else:
        runs = report["runs"]
        cols = st.columns(3)
        for col, run in zip(cols, runs):
            col.metric(run["architecture"], f"{run['vrsr_percent']:.2f}%", f"Evidence {run['evidence_coverage']:.2f}%")
        st.vega_lite_chart({"data": {"values": chart_data(report)}, "mark": "bar", "encoding": {"x": {"field": "stage", "type": "nominal", "axis": {"labelAngle": 0}}, "y": {"field": "vrsr", "type": "quantitative", "scale": {"domain": [0, 100]}}, "tooltip": [{"field": "vrsr", "type": "quantitative"}]}}, use_container_width=True)
        st.metric("Baseline → final VRSR", f"+{runs[-1]['vrsr_percent']-runs[0]['vrsr_percent']:.1f} pp")
        st.metric("Phase 4 → verifier VRSR", f"+{runs[-1]['vrsr_percent']-runs[1]['vrsr_percent']:.1f} pp")
        st.caption("Reliability came at a cost: latency and recorded tokens increased. Additional agents must earn their cost.")
with recorded:
    st.caption("Historical recorded run — no API call")
    cases = playback_cases()
    if not cases:
        st.warning("No historical playback trajectories found.")
    else:
        case = st.radio("Demo path", ["Judge Demo — revised success", "Explore known limitation"], horizontal=True)
        case = judge_demo_case() if case.startswith("Judge") else "CASE-003"
        stages = playback("resolveops-phase5a-001", case)
        inv = stages.get("investigator-v1", {}).get("output", {})
        st.subheader("Evidence Trail")
        for group, cards in evidence_cards(inv).items():
            if cards:
                st.markdown(f"**{group.upper()}**")
                for card in cards: st.markdown(f"<div class='card'><b>{card['statement']}</b><br><span class='muted'>{card['source_id']} · {card['tool_name']}</span></div>", unsafe_allow_html=True)
        st.caption("OBSERVED FACTS are distinct from Investigator hypotheses.")
        for name, data in workflow_stages(stages):
            with st.expander(name.replace("-", " ").title(), expanded=name == "investigator-v1"):
                output = data.get("output") or {}
                if name == "verifier-v1":
                    st.success("✓ APPROVED") if output.get("approved") else st.warning("⚠ REVISION REQUESTED")
                    if output.get("issues"): st.caption(" · ".join(display_label(item.get("category")) for item in output["issues"]))
                st.write(output.get("investigation_summary") or output.get("customer_response") or output.get("feedback") or data.get("error") or "Recorded stage.")
                with st.expander("Raw recorded JSON"): st.json(output)
        final = stages.get("resolver-revision-v1") or stages.get("resolver-v1")
        if final and final.get("output"):
            answer = final["output"]
            st.subheader("Resolution Packet")
            cols = st.columns(4)
            for col, key in zip(cols, ("root_cause_id", "recommended_action_id", "escalate", "confidence")): col.markdown(f"<div class='card'><b>{key.replace('_', ' ').upper()}</b><br>{display_label(str(answer.get(key))) if key != 'confidence' else answer.get(key)}</div>", unsafe_allow_html=True)
            st.write(answer.get("customer_response"))
            gate = safety_gate(answer.get("recommended_action_id"))
            st.caption("SIMULATED — NO REAL SYSTEM CHANGES")
            st.write(f"Safety gate: {gate.approval_status.value} — {gate.summary}")
            if gate.approval_required:
                left, right = st.columns(2)
                if left.button("Approve simulated action"):
                    st.success(safety_gate(answer.get("recommended_action_id"), HumanApproval.APPROVE).summary)
                if right.button("Reject simulated action"):
                    st.error(safety_gate(answer.get("recommended_action_id"), HumanApproval.REJECT).summary)
        rows = comparison_rows(stages)
        if any(row["changed"] for row in rows):
            st.subheader("Verifier before vs after")
            st.dataframe(rows, hide_index=True, use_container_width=True)
            changed = [row["label"] for row in rows if row["changed"]]
            st.write("**What the verifier changed:** " + ", ".join(changed))
        if case == "CASE-003": st.info("Known limitation: shared conservative bias. Independent verification reduces error, but does not guarantee independent judgment.")
