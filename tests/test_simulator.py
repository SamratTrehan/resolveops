"""Offline tests for the deterministic Phase 1 support environment."""

from datetime import datetime

import pytest
from pydantic import ValidationError

from resolveops.domain import Customer, ToolResult
from resolveops.tools import (
    SupportEnvironment,
    check_service_outages,
    get_account_status,
    get_device_status,
    get_ticket_history,
    run_connectivity_diagnostics,
    search_knowledge_base,
)


@pytest.fixture
def environment() -> SupportEnvironment:
    return SupportEnvironment()


def test_synthetic_data_loads(environment: SupportEnvironment) -> None:
    assert len(environment.customers) == 6
    assert len(environment.accounts) == 6
    assert len(environment.devices) == 11
    assert len(environment.articles) == 8


def test_relationships_are_valid(environment: SupportEnvironment) -> None:
    assert {account.customer_id for account in environment.accounts.values()} == set(environment.customers)
    assert all(device.account_id in environment.accounts for device in environment.devices.values())
    assert all(ticket.customer_id in environment.customers for ticket in environment.ticket_history)


def test_account_lookup_returns_account_and_devices() -> None:
    result = get_account_status("CUS-003")
    assert result.success
    assert result.source_ids == ["CUS-003", "ACC-003"]
    assert result.evidence[1].data["provisioning_status"] == "awaiting_gateway_activation"


def test_device_lookup_returns_current_state() -> None:
    result = get_device_status("DEV-007")
    assert result.success
    assert result.evidence[0].data["status"]["online"] is False


def test_outage_positive_customer() -> None:
    result = check_service_outages("CUS-002")
    assert result.success
    assert result.source_ids == ["CUS-002", "OUT-001"]
    assert "Active outage" in result.summary


def test_outage_negative_customer() -> None:
    result = check_service_outages("CUS-001")
    assert result.success
    assert result.source_ids == ["CUS-001"]
    assert "No active outage" in result.summary


def test_gateway_connectivity_diagnostics_are_structured() -> None:
    result = run_connectivity_diagnostics("DEV-008")
    assert result.success
    assert result.evidence[0].data == {
        "gateway_reachable": True,
        "wan_connected": True,
        "wan_ip_available": True,
        "dns_reachable": False,
        "local_connectivity": True,
        "signal_health": "degraded",
    }


def test_ticket_history_is_chronological() -> None:
    result = get_ticket_history("CUS-002")
    created_at = [datetime.fromisoformat(item.data["created_at"]) for item in result.evidence]
    assert created_at == sorted(created_at)


def test_kb_search_ranks_gateway_activation_article_first() -> None:
    result = search_knowledge_base("gateway activation provisioning")
    assert result.success
    assert result.evidence[0].entity_id == "KB-001"
    assert result.evidence[0].data["score"] > 0


def test_kb_search_is_repeatable() -> None:
    assert search_knowledge_base("regional outage internet").model_dump() == search_knowledge_base(
        "regional outage internet"
    ).model_dump()


@pytest.mark.parametrize("tool", [get_account_status, check_service_outages, get_ticket_history])
def test_invalid_customer_ids_return_structured_failures(tool: object) -> None:
    result = tool("CUS-999")
    assert not result.success
    assert result.error == "Customer not found: CUS-999"
    assert result.evidence == []


def test_invalid_device_id_returns_structured_failure() -> None:
    result = get_device_status("DEV-999")
    assert not result.success
    assert result.error == "Device not found: DEV-999"


def test_unsupported_diagnostic_target_returns_failure() -> None:
    result = run_connectivity_diagnostics("DEV-009")
    assert not result.success
    assert "Unsupported diagnostic target" in result.error


def test_empty_kb_query_returns_failure() -> None:
    result = search_knowledge_base("   ")
    assert not result.success
    assert result.error == "Empty KB query."


def test_schema_validation_rejects_invalid_customer_id() -> None:
    with pytest.raises(ValidationError):
        Customer(id="customer-1", display_name="Synthetic", service_area="District Aurora")


def test_tool_results_round_trip_as_json() -> None:
    result = get_device_status("DEV-001")
    assert ToolResult.model_validate_json(result.model_dump_json()) == result


def test_repeat_calls_return_equivalent_results() -> None:
    assert run_connectivity_diagnostics("DEV-003").model_dump() == run_connectivity_diagnostics(
        "DEV-003"
    ).model_dump()
