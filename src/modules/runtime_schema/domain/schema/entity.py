from dataclasses import dataclass
from datetime import datetime

from src.modules.shared import EntityIdVO


@dataclass(slots=True)
class DataSourceEntity:
    id: EntityIdVO
    tenant_id: EntityIdVO
    created_at: datetime
    updated_at: datetime
    type: str
    schema: str
