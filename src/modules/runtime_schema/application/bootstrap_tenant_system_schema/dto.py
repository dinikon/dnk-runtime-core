from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


@dataclass(slots=True, frozen=True)
class BootstrapTenantSystemSchemaCommandDTO:
    tenant_id: UUID
    data_source_id: UUID
    schema: str

