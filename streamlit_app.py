"""Streamlit judge demo; historical playback is read-only."""

import os

import streamlit as st

from resolveops.app.demo_data import comparison_report, playback, playback_cases
from resolveops.agents.resolveops.safety import HumanApproval, safety_gate


st.set_page_config(page_title="ResolveOps", layout="wide")
st.title("ResolveOps")
st.caption("Evidence-grounded technical support with independent verification and human approval for consequential actions.")
st.info("Synthetic demo only — do not enter real customer data, credentials, or private information.")

overview, improvement, recorded = st.tabs(["Resolve a ticket", "Measured Improvement", "Historical playback"])
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
    report = comparison_report()
    if not report:
        st.warning("Comparison report is unavailable. Run `python -m resolveops.evaluation.report_experiments`.")
    else:
        runs = report["runs"]
        cols = st.columns(3)
        for col, run in zip(cols, runs):
            col.metric(run["architecture"], f"{run['vrsr_percent']:.2f}%", f"Evidence {run['evidence_coverage']:.2f}%")
        st.bar_chart({"VRSR": {run["architecture"]: run["vrsr_percent"] for run in runs}, "Evidence coverage": {run["architecture"]: run["evidence_coverage"] for run in runs}})
        st.caption("Reliability improved, while latency and recorded token use increased. Additional agents must earn their cost.")
with recorded:
    st.caption("Historical recorded run — no API call")
    cases = playback_cases()
    if not cases:
        st.warning("No historical playback trajectories found.")
    else:
        case = st.selectbox("Recorded case", cases, index=cases.index("CASE-003") if "CASE-003" in cases else 0)
        stages = playback("resolveops-phase5a-001", case)
        for name, data in stages.items():
            with st.expander(name.replace("-", " ").title(), expanded=name == "investigator-v1"):
                output = data.get("output") or {}
                st.write(output.get("investigation_summary") or output.get("customer_response") or data.get("error") or "Recorded stage.")
                st.json(output)
        final = stages.get("resolver-revision-v1") or stages.get("resolver-v1")
        if final and final.get("output"):
            answer = final["output"]
            st.subheader("Resolution Packet")
            st.write(f"**Root cause:** {answer.get('root_cause_id')} · **Action:** {answer.get('recommended_action_id')} · **Escalate:** {answer.get('escalate')}")
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
