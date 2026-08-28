"""Pydantic models for ResolveOps' synthetic support environment."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class Customer(BaseModel):
    id: str = Field(pattern=r"^CUS-\d{3}$")
    display_name: str
    service_area: str


class Account(BaseModel):
    id: str = Field(pattern=r"^ACC-\d{3}$")
    customer_id: str = Field(pattern=r"^CUS-\d{3}$")
    standing: Literal["current", "past_due"]
    service_activation: Literal["active", "pending"]
    provisioning_status: Literal["complete", "awaiting_gateway_activation"]
    service_plan: str


class DeviceStatus(BaseModel):
    online: bool
    connection_state: str
    firmware_version: str
    local_connectivity: bool | None = None
    gateway_reachable: bool | None = None
    wan_connected: bool | None = None
    wan_ip_available: bool | None = None
    dns_reachable: bool | None = None
    signal_health: str | None = None


class Device(BaseModel):
    id: str = Field(pattern=r"^DEV-\d{3}$")
    account_id: str = Field(pattern=r"^ACC-\d{3}$")
    device_type: Literal["gateway", "camera", "sensor"]
    label: str
    status: DeviceStatus


class ServiceOutage(BaseModel):
    id: str = Field(pattern=r"^OUT-\d{3}$")
    affected_areas: list[str]
    status: Literal["active", "resolved"]
    started_at: datetime
    summary: str


class TicketHistoryEntry(BaseModel):
    id: str = Field(pattern=r"^TKT-\d{3}$")
    customer_id: str = Field(pattern=r"^CUS-\d{3}$")
    created_at: datetime
    category: str
    summary: str
    outcome: str


class KnowledgeBaseArticle(BaseModel):
    id: str = Field(pattern=r"^KB-\d{3}$")
    title: str
    tags: list[str]
    content: str


class ToolEvidence(BaseModel):
    source: str
    entity_id: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)
    summary: str


class ToolResult(BaseModel):
    tool_name: str
    success: bool
    evidence: list[ToolEvidence] = Field(default_factory=list)
    summary: str
    source_ids: list[str] = Field(default_factory=list)
    error: str | None = None
