"""Deterministic, read-only support diagnostics backed by local synthetic data."""

import json
import re
from functools import lru_cache
from pathlib import Path

from resolveops.domain import (
    Account,
    Customer,
    Device,
    KnowledgeBaseArticle,
    ServiceOutage,
    TicketHistoryEntry,
    ToolEvidence,
    ToolResult,
)


def _default_data_root() -> Path:
    return Path(__file__).resolve().parents[2] / "data"


def _words(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def _load_article(path: Path) -> KnowledgeBaseArticle:
    lines = path.read_text(encoding="utf-8").splitlines()
    if lines[:1] != ["---"]:
        raise ValueError(f"Knowledge-base article has no metadata: {path.name}")
    try:
        end = lines.index("---", 1)
    except ValueError as error:
        raise ValueError(f"Knowledge-base article has invalid metadata: {path.name}") from error
    metadata = dict(line.split(": ", 1) for line in lines[1:end])
    return KnowledgeBaseArticle(
        id=metadata["id"],
        title=metadata["title"],
        tags=[tag.strip() for tag in metadata["tags"].split(",")],
        content="\n".join(lines[end + 1 :]).strip(),
    )


class SupportEnvironment:
    """A compact in-memory view of the JSON and Markdown synthetic world."""

    def __init__(self, data_root: Path | None = None) -> None:
        root = data_root or _default_data_root()
        raw = json.loads((root / "support_world.json").read_text(encoding="utf-8"))
        self.customers = {item.id: item for item in map(Customer.model_validate, raw["customers"])}
        self.accounts = {item.id: item for item in map(Account.model_validate, raw["accounts"])}
        self.devices = {item.id: item for item in map(Device.model_validate, raw["devices"])}
        self.outages = [ServiceOutage.model_validate(item) for item in raw["outages"]]
        self.ticket_history = [
            TicketHistoryEntry.model_validate(item) for item in raw["ticket_history"]
        ]
        self.articles = [_load_article(path) for path in sorted((root / "knowledge_base").glob("*.md"))]
        self._validate_relationships()

    def _validate_relationships(self) -> None:
        if len(self.accounts) != len(self.customers):
            raise ValueError("Each synthetic customer must have one account.")
        if {account.customer_id for account in self.accounts.values()} != set(self.customers):
            raise ValueError("Account-to-customer relationships are invalid.")
        if any(device.account_id not in self.accounts for device in self.devices.values()):
            raise ValueError("Device-to-account relationship is invalid.")
        if any(ticket.customer_id not in self.customers for ticket in self.ticket_history):
            raise ValueError("Ticket-to-customer relationship is invalid.")

    @staticmethod
    def _failure(tool_name: str, error: str) -> ToolResult:
        return ToolResult(tool_name=tool_name, success=False, summary=error, error=error)

    @staticmethod
    def _success(tool_name: str, evidence: list[ToolEvidence], summary: str) -> ToolResult:
        return ToolResult(
            tool_name=tool_name,
            success=True,
            evidence=evidence,
            summary=summary,
            source_ids=list(dict.fromkeys(item.entity_id for item in evidence if item.entity_id)),
        )

    def get_account_status(self, customer_id: str) -> ToolResult:
        customer = self.customers.get(customer_id)
        if not customer:
            return self._failure("get_account_status", f"Customer not found: {customer_id}")
        account = next(account for account in self.accounts.values() if account.customer_id == customer_id)
        devices = [device for device in self.devices.values() if device.account_id == account.id]
        evidence = [
            ToolEvidence(source="synthetic_world", entity_id=customer.id, data=customer.model_dump(mode="json"), summary="Synthetic customer record."),
            ToolEvidence(source="synthetic_world", entity_id=account.id, data=account.model_dump(mode="json"), summary="Synthetic account status."),
            ToolEvidence(
                source="synthetic_world",
                entity_id=account.id,
                data={"device_ids": [device.id for device in devices]},
                summary="Devices registered to the synthetic account.",
            ),
        ]
        return self._success("get_account_status", evidence, f"Account {account.id} is {account.service_activation}.")

    def get_device_status(self, device_id: str) -> ToolResult:
        device = self.devices.get(device_id)
        if not device:
            return self._failure("get_device_status", f"Device not found: {device_id}")
        return self._success(
            "get_device_status",
            [ToolEvidence(source="synthetic_world", entity_id=device.id, data=device.model_dump(mode="json"), summary="Synthetic device state.")],
            f"Device {device.id} is {'online' if device.status.online else 'offline'}.",
        )

    def run_connectivity_diagnostics(self, device_id: str) -> ToolResult:
        device = self.devices.get(device_id)
        if not device:
            return self._failure("run_connectivity_diagnostics", f"Device not found: {device_id}")
        if device.device_type != "gateway":
            return self._failure(
                "run_connectivity_diagnostics",
                f"Unsupported diagnostic target: {device_id} ({device.device_type})",
            )
        status = device.status
        diagnostic_data = {
            "gateway_reachable": status.gateway_reachable,
            "wan_connected": status.wan_connected,
            "wan_ip_available": status.wan_ip_available,
            "dns_reachable": status.dns_reachable,
            "local_connectivity": status.local_connectivity,
            "signal_health": status.signal_health,
        }
        return self._success(
            "run_connectivity_diagnostics",
            [ToolEvidence(source="synthetic_diagnostics", entity_id=device.id, data=diagnostic_data, summary="Deterministic gateway connectivity checks.")],
            f"Connectivity diagnostics completed for {device.id}.",
        )

    def check_service_outages(self, customer_id: str) -> ToolResult:
        customer = self.customers.get(customer_id)
        if not customer:
            return self._failure("check_service_outages", f"Customer not found: {customer_id}")
        active = [
            outage for outage in self.outages
            if outage.status == "active" and customer.service_area in outage.affected_areas
        ]
        evidence = [
            ToolEvidence(
                source="synthetic_world",
                entity_id=customer.id,
                data={"service_area": customer.service_area},
                summary="Synthetic service area used for outage lookup.",
            )
        ]
        evidence.extend(
            ToolEvidence(source="synthetic_outage_feed", entity_id=outage.id, data=outage.model_dump(mode="json"), summary=outage.summary)
            for outage in active
        )
        summary = (
            f"Active outage found for {customer.service_area}."
            if active else f"No active outage found for {customer.service_area}."
        )
        return self._success("check_service_outages", evidence, summary)

    def get_ticket_history(self, customer_id: str) -> ToolResult:
        if customer_id not in self.customers:
            return self._failure("get_ticket_history", f"Customer not found: {customer_id}")
        tickets = sorted(
            (ticket for ticket in self.ticket_history if ticket.customer_id == customer_id),
            key=lambda ticket: ticket.created_at,
        )
        evidence = [
            ToolEvidence(source="synthetic_ticket_history", entity_id=ticket.id, data=ticket.model_dump(mode="json"), summary=ticket.summary)
            for ticket in tickets
        ]
        return self._success("get_ticket_history", evidence, f"Found {len(tickets)} ticket-history entries.")

    def search_knowledge_base(self, query: str, limit: int = 3) -> ToolResult:
        query_words = _words(query)
        if not query_words:
            return self._failure("search_knowledge_base", "Empty KB query.")
        if limit < 1:
            return self._failure("search_knowledge_base", "KB search limit must be at least 1.")
        matches = []
        for article in self.articles:
            title_words = _words(article.title)
            tag_words = _words(" ".join(article.tags))
            content_words = _words(article.content)
            score = 3 * len(query_words & title_words) + 2 * len(query_words & tag_words) + len(query_words & content_words)
            if score:
                excerpt = article.content[:220]
                matches.append((score, article, excerpt))
        matches.sort(key=lambda item: (-item[0], item[1].id))
        evidence = [
            ToolEvidence(
                source="synthetic_knowledge_base",
                entity_id=article.id,
                data={"article_id": article.id, "title": article.title, "score": score, "excerpt": excerpt},
                summary=f"KB match: {article.title}",
            )
            for score, article, excerpt in matches[:limit]
        ]
        return self._success("search_knowledge_base", evidence, f"Found {len(evidence)} KB matches.")


@lru_cache(maxsize=1)
def default_environment() -> SupportEnvironment:
    return SupportEnvironment()


def get_account_status(customer_id: str) -> ToolResult:
    return default_environment().get_account_status(customer_id)


def get_device_status(device_id: str) -> ToolResult:
    return default_environment().get_device_status(device_id)


def run_connectivity_diagnostics(device_id: str) -> ToolResult:
    return default_environment().run_connectivity_diagnostics(device_id)


def check_service_outages(customer_id: str) -> ToolResult:
    return default_environment().check_service_outages(customer_id)


def get_ticket_history(customer_id: str) -> ToolResult:
    return default_environment().get_ticket_history(customer_id)


def search_knowledge_base(query: str, limit: int = 3) -> ToolResult:
    return default_environment().search_knowledge_base(query, limit)
