"""Deterministic, read-only synthetic support tools."""

from .simulator import (
    SupportEnvironment,
    check_service_outages,
    default_environment,
    get_account_status,
    get_device_status,
    get_ticket_history,
    run_connectivity_diagnostics,
    search_knowledge_base,
)

__all__ = [
    "SupportEnvironment",
    "check_service_outages",
    "default_environment",
    "get_account_status",
    "get_device_status",
    "get_ticket_history",
    "run_connectivity_diagnostics",
    "search_knowledge_base",
]
