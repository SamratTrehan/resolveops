"""Deterministic human approval gate for synthetic actions only."""

from enum import StrEnum

from pydantic import BaseModel

from resolveops.domain.action_safety import requires_human_approval
from resolveops.domain.support_ontology import ActionId


class HumanApproval(StrEnum):
    APPROVE = "approve"
    REJECT = "reject"


class ApprovalStatus(StrEnum):
    NOT_REQUIRED = "not_required"
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class SafetyGateRecord(BaseModel):
    action_id: ActionId
    approval_required: bool
    approval_status: ApprovalStatus
    human_decision: HumanApproval | None = None
    reason: str
    simulated: bool = True
    execution_status: str
    summary: str


def safety_gate(action_id: ActionId, decision: HumanApproval | None = None) -> SafetyGateRecord:
    required = requires_human_approval(action_id)
    if not required:
        return SafetyGateRecord(action_id=action_id, approval_required=False, approval_status=ApprovalStatus.NOT_REQUIRED, reason="Instructional or informational action; no synthetic state change.", execution_status="ready", summary="No approval required; no action was executed.")
    if decision is HumanApproval.APPROVE:
        return SafetyGateRecord(action_id=action_id, approval_required=True, approval_status=ApprovalStatus.APPROVED, human_decision=decision, reason="Gateway activation may change synthetic provisioning state.", execution_status="executed", summary="Approved synthetic execution would be allowed; no external system was contacted.")
    if decision is HumanApproval.REJECT:
        return SafetyGateRecord(action_id=action_id, approval_required=True, approval_status=ApprovalStatus.REJECTED, human_decision=decision, reason="Gateway activation may change synthetic provisioning state.", execution_status="blocked_rejected", summary="Synthetic execution blocked by human rejection.")
    return SafetyGateRecord(action_id=action_id, approval_required=True, approval_status=ApprovalStatus.PENDING, reason="Gateway activation may change synthetic provisioning state.", execution_status="blocked_pending_approval", summary="Synthetic execution blocked pending explicit human approval.")
