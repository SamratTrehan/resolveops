"""Public, case-agnostic output vocabulary shared by all ResolveOps workflows."""

from enum import StrEnum


class RootCauseId(StrEnum):
    REGIONAL_OUTAGE = "regional_outage"
    PENDING_GATEWAY_PROVISIONING = "pending_gateway_provisioning"
    CAMERA_RECONNECT_NEEDED = "camera_reconnect_needed"
    DNS_RESOLUTION_FAILURE = "dns_resolution_failure"
    LOCAL_WIFI_CONFIGURATION = "local_wifi_configuration"
    ACCOUNT_STANDING_QUESTION = "account_standing_question"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class ActionId(StrEnum):
    COMMUNICATE_OUTAGE_STATUS = "communicate_outage_status"
    GUIDE_GATEWAY_ACTIVATION = "guide_gateway_activation"
    GUIDE_CAMERA_RECONNECT = "guide_camera_reconnect"
    GUIDE_DNS_RECOVERY = "guide_dns_recovery"
    GUIDE_WIFI_RECONNECT = "guide_wifi_reconnect"
    REVIEW_ACCOUNT_NOTICE = "review_account_notice"
    ESCALATE_FOR_MORE_EVIDENCE = "escalate_for_more_evidence"


ROOT_CAUSE_DESCRIPTIONS: dict[RootCauseId, str] = {
    RootCauseId.REGIONAL_OUTAGE: "Service interruption affecting the customer's area.",
    RootCauseId.PENDING_GATEWAY_PROVISIONING: "Replacement or new gateway activation/provisioning is incomplete.",
    RootCauseId.CAMERA_RECONNECT_NEEDED: "Camera needs reconnection or reconfiguration rather than being proven defective.",
    RootCauseId.DNS_RESOLUTION_FAILURE: "Connectivity exists but DNS/name resolution is unavailable.",
    RootCauseId.LOCAL_WIFI_CONFIGURATION: "Issue is local to Wi-Fi/client configuration rather than upstream service.",
    RootCauseId.ACCOUNT_STANDING_QUESTION: "Concern relates to an account notice without evidence of service suspension.",
    RootCauseId.INSUFFICIENT_EVIDENCE: "Available evidence does not support a reliable root cause.",
}

ACTION_DESCRIPTIONS: dict[ActionId, str] = {
    ActionId.COMMUNICATE_OUTAGE_STATUS: "Communicate the known area-outage status and expected next step.",
    ActionId.GUIDE_GATEWAY_ACTIVATION: "Guide the customer through gateway activation or provisioning completion.",
    ActionId.GUIDE_CAMERA_RECONNECT: "Guide reconnection of a camera to the available gateway/network.",
    ActionId.GUIDE_DNS_RECOVERY: "Guide standard recovery and retest steps for a DNS-resolution problem.",
    ActionId.GUIDE_WIFI_RECONNECT: "Guide local Wi-Fi/client reconnection or configuration recovery.",
    ActionId.REVIEW_ACCOUNT_NOTICE: "Explain and direct review of an account-standing notice.",
    ActionId.ESCALATE_FOR_MORE_EVIDENCE: "Escalate because the available evidence is insufficient for a reliable resolution.",
}


def public_ontology_text() -> str:
    """Render the shared public output contract for an agent instruction."""
    roots = "\n".join(f"- {item.value}: {ROOT_CAUSE_DESCRIPTIONS[item]}" for item in RootCauseId)
    actions = "\n".join(f"- {item.value}: {ACTION_DESCRIPTIONS[item]}" for item in ActionId)
    return f"Public root-cause IDs (choose exactly one):\n{roots}\n\nPublic action IDs (choose exactly one):\n{actions}"
