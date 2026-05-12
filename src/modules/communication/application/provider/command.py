from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID


@dataclass(frozen=True, slots=True)
class RegisterProviderConnectorCommand:
    tenant_id: UUID
    yaml_content: str


@dataclass(frozen=True, slots=True)
class CreateProviderConnectionCommand:
    tenant_id: UUID
    provider_connector_id: UUID
    connection_code: str
    connection_name: str
    channel_code: str
    config: dict[str, Any] = field(default_factory=dict)
    secrets: dict[str, Any] = field(default_factory=dict)
    secret_ref: str | None = None


__all__ = [
    "CreateProviderConnectionCommand",
    "RegisterProviderConnectorCommand",
]
