from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CreateSchemaCommandDTO:
    tenant_id: str
    type: str
    schema_name: str
