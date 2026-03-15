from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class DataSourceDTO:
    id: str
    tenant_id: str
    created_at: datetime
    updated_at: datetime
    type: str
    schema_name: str
