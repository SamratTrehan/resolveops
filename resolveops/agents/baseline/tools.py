"""Thin SDK adapters over the SDK-independent Phase 1 simulator."""

from dataclasses import dataclass, field

from agents import RunContextWrapper, function_tool

from resolveops.agents.baseline.records import RecordedToolCall
from resolveops.domain import ToolResult
from resolveops.tools import (
    check_service_outages as simulator_check_service_outages,
    get_account_status as simulator_get_account_status,
    get_device_status as simulator_get_device_status,
    get_ticket_history as simulator_get_ticket_history,
    run_connectivity_diagnostics as simulator_run_connectivity_diagnostics,
    search_knowledge_base as simulator_search_knowledge_base,
)


@dataclass
class BaselineRunContext:
    tool_calls: list[RecordedToolCall] = field(default_factory=list)

    def record(self, tool_name: str, arguments: dict[str, object], result: ToolResult) -> ToolResult:
        self.tool_calls.append(RecordedToolCall(tool_name=tool_name, arguments=arguments, result=result))
        return result


def call_get_account_status(customer_id: str) -> ToolResult:
    return simulator_get_account_status(customer_id)


def call_get_device_status(device_id: str) -> ToolResult:
    return simulator_get_device_status(device_id)


def call_run_connectivity_diagnostics(device_id: str) -> ToolResult:
    return simulator_run_connectivity_diagnostics(device_id)


def call_check_service_outages(customer_id: str) -> ToolResult:
    return simulator_check_service_outages(customer_id)


def call_get_ticket_history(customer_id: str) -> ToolResult:
    return simulator_get_ticket_history(customer_id)


def call_search_knowledge_base(query: str, limit: int = 3) -> ToolResult:
    return simulator_search_knowledge_base(query, limit)


@function_tool
def get_account_status(ctx: RunContextWrapper[BaselineRunContext], customer_id: str) -> ToolResult:
    """Return synthetic account, service activation, and registered-device evidence."""
    return ctx.context.record("get_account_status", {"customer_id": customer_id}, call_get_account_status(customer_id))


@function_tool
def get_device_status(ctx: RunContextWrapper[BaselineRunContext], device_id: str) -> ToolResult:
    """Return current synthetic device status and stable source IDs."""
    return ctx.context.record("get_device_status", {"device_id": device_id}, call_get_device_status(device_id))


@function_tool
def run_connectivity_diagnostics(ctx: RunContextWrapper[BaselineRunContext], device_id: str) -> ToolResult:
    """Run deterministic gateway connectivity checks for a supported synthetic device."""
    return ctx.context.record(
        "run_connectivity_diagnostics",
        {"device_id": device_id},
        call_run_connectivity_diagnostics(device_id),
    )


@function_tool
def check_service_outages(ctx: RunContextWrapper[BaselineRunContext], customer_id: str) -> ToolResult:
    """Check active synthetic service outages for the customer's area."""
    return ctx.context.record("check_service_outages", {"customer_id": customer_id}, call_check_service_outages(customer_id))


@function_tool
def get_ticket_history(ctx: RunContextWrapper[BaselineRunContext], customer_id: str) -> ToolResult:
    """Return chronological synthetic ticket history for a customer."""
    return ctx.context.record("get_ticket_history", {"customer_id": customer_id}, call_get_ticket_history(customer_id))


@function_tool
def search_knowledge_base(ctx: RunContextWrapper[BaselineRunContext], query: str, limit: int = 3) -> ToolResult:
    """Search local synthetic knowledge-base articles with deterministic lexical ranking."""
    return ctx.context.record(
        "search_knowledge_base",
        {"query": query, "limit": limit},
        call_search_knowledge_base(query, limit),
    )


DIRECT_TOOL_WRAPPERS = {
    "get_account_status": call_get_account_status,
    "get_device_status": call_get_device_status,
    "run_connectivity_diagnostics": call_run_connectivity_diagnostics,
    "check_service_outages": call_check_service_outages,
    "get_ticket_history": call_get_ticket_history,
    "search_knowledge_base": call_search_knowledge_base,
}

BASELINE_TOOLS = [
    get_account_status,
    get_device_status,
    run_connectivity_diagnostics,
    check_service_outages,
    get_ticket_history,
    search_knowledge_base,
]
