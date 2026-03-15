from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class CreateSchemaCommandDTO:
    tenant_id: str
    schema_name: str
    schema_type: str = "postgres"
    schema_id: str | None = None


@dataclass(frozen=True, slots=True)
class CreateSchemaResultDTO:
    schema_id: str
    tenant_id: str
    schema_name: str
    schema_type: str
    created_at: datetime
    updated_at: datetime

