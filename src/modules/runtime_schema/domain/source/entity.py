from dataclasses import dataclass
from datetime import datetime

from modules.runtime_schema.domain.source.value_object import DataSourceIdVO
from modules.shared.domain.value_object.entity_id import EntityIdVO


@dataclass(slots=True)
class DataSource:
    id: DataSourceIdVO
    created_at: datetime
    updated_at: datetime
    tenant_id: EntityIdVO

    type: str
    schema: str
    is_system: bool
    is_remote: bool
    dsn: str | None
