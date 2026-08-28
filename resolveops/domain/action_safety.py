"""Public, conservative safety classification for simulated support actions."""

from resolveops.domain.support_ontology import ActionId


APPROVAL_REQUIRED_ACTIONS = frozenset({ActionId.GUIDE_GATEWAY_ACTIVATION})


def requires_human_approval(action_id: ActionId) -> bool:
    """Gateway activation can imply a provisioning-state change; all else is guidance only."""
    return action_id in APPROVAL_REQUIRED_ACTIONS
