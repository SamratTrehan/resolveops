"""Session-local execution for the demo's one consequential synthetic action."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import MutableMapping

from pydantic import BaseModel

from resolveops.agents.resolveops.safety import HumanApproval
from resolveops.domain.action_safety import requires_human_approval
from resolveops.domain.support_ontology import ActionId
from resolveops.tools import default_environment


SANDBOX_STATE_KEY = "resolveops_synthetic_sandbox"
SANDBOX_AUDIT_KEY = "resolveops_synthetic_action_audit"


class SandboxError(ValueError):
    """A safe, user-facing reason why synthetic execution was blocked."""


class SandboxProvisioningState(BaseModel):
    service_activation: str
    provisioning_status: str
    gateway_connection_state: str


class SyntheticActionRequest(BaseModel):
    context: str
    run_or_case_id: str
    customer_id: str
    primary_device_id: str | None
    action_id: ActionId
    human_decision: HumanApproval | None = None


class SyntheticActionResult(BaseModel):
    context: str
    run_or_case_id: str
    action_id: ActionId | None = None
    safety_class: str = "approval_required"
    customer_id: str
    account_id: str | None = None
    device_id: str | None = None
    human_decision: HumanApproval | None = None
    before_state: SandboxProvisioningState | None = None
    after_state: SandboxProvisioningState | None = None
    executed: bool = False
    execution_status: str
    blocked_reason: str | None = None
    timestamp: datetime


def _target_key(context: str, account_id: str) -> str:
    return f"{context}:{account_id}"


def _state_get(state: MutableMapping[str, object], key: str, default: object) -> object:
    try:
        return state[key]
    except KeyError:
        return default


def _target(customer_id: str, primary_device_id: str | None):
    environment = default_environment()
    customer = environment.customers.get(customer_id)
    if customer is None:
        raise SandboxError("Synthetic customer target was not found.")
    if not primary_device_id:
        raise SandboxError("A gateway target is required for this synthetic action.")
    device = environment.devices.get(primary_device_id)
    if device is None or device.device_type != "gateway":
        raise SandboxError("Synthetic gateway target was not found.")
    account = environment.accounts.get(device.account_id)
    if account is None or account.customer_id != customer.id:
        raise SandboxError("Synthetic account and gateway relationship is invalid.")
    return account, device


def _canonical_state(customer_id: str, primary_device_id: str | None) -> tuple[object, object, SandboxProvisioningState]:
    account, device = _target(customer_id, primary_device_id)
    return account, device, SandboxProvisioningState(
        service_activation=account.service_activation,
        provisioning_status=account.provisioning_status,
        gateway_connection_state=device.status.connection_state,
    )


def _overlay(state: MutableMapping[str, object]) -> dict[str, object]:
    value = _state_get(state, SANDBOX_STATE_KEY, {})
    if not isinstance(value, dict):
        raise SandboxError("Synthetic sandbox state is invalid; execution was blocked.")
    return value


def read_sandbox_state(
    state: MutableMapping[str, object], context: str, customer_id: str, primary_device_id: str | None
) -> SandboxProvisioningState:
    """Read the canonical target state with a validated session overlay, if present."""
    account, _device, canonical = _canonical_state(customer_id, primary_device_id)
    stored = _overlay(state).get(_target_key(context, account.id))
    if stored is None:
        return canonical
    if not isinstance(stored, dict):
        raise SandboxError("Synthetic sandbox state is invalid; execution was blocked.")
    try:
        return SandboxProvisioningState.model_validate(stored)
    except (TypeError, ValueError) as error:
        raise SandboxError("Synthetic sandbox state is invalid; execution was blocked.") from error


def _result(
    request: SyntheticActionRequest,
    *,
    timestamp: datetime,
    status: str,
    account_id: str | None = None,
    device_id: str | None = None,
    before: SandboxProvisioningState | None = None,
    after: SandboxProvisioningState | None = None,
    executed: bool = False,
    reason: str | None = None,
) -> SyntheticActionResult:
    return SyntheticActionResult(
        context=request.context,
        run_or_case_id=request.run_or_case_id,
        action_id=request.action_id if isinstance(request.action_id, ActionId) else None,
        customer_id=request.customer_id,
        account_id=account_id,
        device_id=device_id,
        human_decision=request.human_decision if isinstance(request.human_decision, HumanApproval) else None,
        before_state=before,
        after_state=after,
        executed=executed,
        execution_status=status,
        blocked_reason=reason,
        timestamp=timestamp,
    )


def _record(state: MutableMapping[str, object], result: SyntheticActionResult) -> SyntheticActionResult:
    audit = _state_get(state, SANDBOX_AUDIT_KEY, {})
    if not isinstance(audit, dict):
        audit = {}
    updated = dict(audit)
    updated[result.context] = result.model_dump(mode="json")
    state[SANDBOX_AUDIT_KEY] = updated
    return result


def action_audit(state: MutableMapping[str, object], context: str) -> SyntheticActionResult | None:
    """Return the last session-local action record for a workflow context."""
    audit = _state_get(state, SANDBOX_AUDIT_KEY, {})
    if not isinstance(audit, dict) or not isinstance(audit.get(context), dict):
        return None
    try:
        return SyntheticActionResult.model_validate(audit[context])
    except (TypeError, ValueError):
        return None


def execute_synthetic_action(
    state: MutableMapping[str, object], request: SyntheticActionRequest, *, now: datetime | None = None
) -> SyntheticActionResult:
    """Validate then commit the single supported synthetic provisioning transition."""
    timestamp = now or datetime.now(timezone.utc)
    if not isinstance(request.action_id, ActionId) or not requires_human_approval(request.action_id):
        return _record(state, _result(request, timestamp=timestamp, status="blocked_validation", reason="This action is not approved for synthetic execution."))
    try:
        account, device, before = _canonical_state(request.customer_id, request.primary_device_id)
        before = read_sandbox_state(state, request.context, request.customer_id, request.primary_device_id)
    except SandboxError as error:
        return _record(state, _result(request, timestamp=timestamp, status="blocked_validation", reason=str(error)))

    target = {"account_id": account.id, "device_id": device.id, "before": before, "after": before}
    if request.human_decision is None:
        return _record(state, _result(request, timestamp=timestamp, status="blocked_pending_approval", reason="Explicit human approval is required.", **target))
    if request.human_decision is not HumanApproval.APPROVE:
        return _record(state, _result(request, timestamp=timestamp, status="blocked_rejected", reason="Synthetic execution was rejected by the human reviewer.", **target))
    if before.provisioning_status == "complete" and before.service_activation == "active":
        return _record(state, _result(request, timestamp=timestamp, status="already_active", reason="Already active — no additional state change required.", **target))
    if not (
        before.provisioning_status == "awaiting_gateway_activation"
        and before.service_activation == "pending"
        and before.gateway_connection_state == "activation_pending"
    ):
        return _record(state, _result(request, timestamp=timestamp, status="blocked_validation", reason="Synthetic action is not applicable to the current gateway state.", **target))

    after = SandboxProvisioningState(
        service_activation="active", provisioning_status="complete", gateway_connection_state="connected"
    )
    overlay = dict(_overlay(state))
    overlay[_target_key(request.context, account.id)] = after.model_dump(mode="json")
    state[SANDBOX_STATE_KEY] = overlay
    verified = read_sandbox_state(state, request.context, request.customer_id, request.primary_device_id)
    return _record(state, _result(request, timestamp=timestamp, status="completed", account_id=account.id, device_id=device.id, before=before, after=verified, executed=True))
