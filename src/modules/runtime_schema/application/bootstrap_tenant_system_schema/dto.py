from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class BootstrapTenantSystemSchemaCommandDTO:
    tenant_id: UUID
    data_source_id: UUID
    schema: str


@dataclass(frozen=True, slots=True)
class BootstrapTenantSystemSchemaResultDTO:
    objects_created: int
    fields_created: int
