from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class RegisterProviderConnectorCommand:
    tenant_id: UUID
    yaml_content: str


__all__ = ["RegisterProviderConnectorCommand"]
