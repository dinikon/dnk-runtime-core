from dataclasses import dataclass
from datetime import datetime
from typing import Self

from src.modules.runtime_schema.domain.data_source.value_object.schama_name import (
    SchemaNameVO,
)
from src.modules.runtime_schema.domain.data_source.value_object.schema_id import (
    SchemaIdVO,
)
from src.modules.runtime_schema.domain.data_source.value_object.schema_type import (
    SchemaTypeVO,
)
from src.modules.shared import EntityIdVO


@dataclass(slots=True)
class DataSourceEntity:
    id: SchemaIdVO
    tenant_id: EntityIdVO
    created_at: datetime
    updated_at: datetime
    type: SchemaTypeVO
    schema_name: SchemaNameVO

    @classmethod
    def create(
        cls,
        _id: SchemaIdVO,
        tenant_id: EntityIdVO,
        type: SchemaTypeVO,
        schema_name: SchemaNameVO,
        now: datetime,
    ) -> Self:
        return cls(
            id=_id,
            tenant_id=tenant_id,
            created_at=now,
            updated_at=now,
            type=type,
            schema_name=schema_name,
        )
