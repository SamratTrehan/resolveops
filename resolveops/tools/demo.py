"""Small, dependency-free demonstration of the deterministic support tools."""

from .simulator import (
    check_service_outages,
    get_account_status,
    get_device_status,
    get_ticket_history,
    run_connectivity_diagnostics,
    search_knowledge_base,
)


def _show(label: str, result: object) -> None:
    print(f"\n{label}")
    print(result.model_dump_json(indent=2))


def main() -> None:
    customer_id = "CUS-002"
    device_id = "DEV-003"
    _show("Account status", get_account_status(customer_id))
    _show("Device status", get_device_status(device_id))
    _show("Connectivity diagnostics", run_connectivity_diagnostics(device_id))
    _show("Outage status", check_service_outages(customer_id))
    _show("Ticket history", get_ticket_history(customer_id))
    _show("KB matches", search_knowledge_base("regional outage internet"))


if __name__ == "__main__":
    main()
