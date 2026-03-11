from dataclasses import dataclass
from datetime import UTC, datetime

from ..errors import DataSourceRemoteDsnRequiredError, DataSourceTimestampOrderError
from .value_object import (
    DataSourceDsnVO,
    DataSourceIdVO,
    DataSourceSchemaVO,
    DataSourceTypeVO,
)
from modules.shared.domain.value_object.entity_id import EntityIdVO


@dataclass(slots=True)
class DataSource:
    id: DataSourceIdVO
    created_at: datetime
    updated_at: datetime
    tenant_id: EntityIdVO

    type: DataSourceTypeVO
    schema: DataSourceSchemaVO
    is_system: bool
    is_remote: bool
    dsn: DataSourceDsnVO | None

    @classmethod
    def create(
        cls,
        *,
        tenant_id: EntityIdVO,
        source_type: DataSourceTypeVO | str,
        schema: DataSourceSchemaVO | str,
        is_system: bool = False,
        is_remote: bool = False,
        dsn: DataSourceDsnVO | str | None = None,
        data_source_id: DataSourceIdVO | None = None,
        created_at: datetime | None = None,
    ) -> "DataSource":
        now = created_at or datetime.now(UTC)
        return cls(
            id=data_source_id or DataSourceIdVO.new(),
            created_at=now,
            updated_at=now,
            tenant_id=tenant_id,
            type=DataSourceTypeVO.from_value(source_type),
            schema=DataSourceSchemaVO.from_value(schema),
            is_system=is_system,
            is_remote=is_remote,
            dsn=DataSourceDsnVO.from_value(dsn) if dsn is not None else None,
        )

    def __post_init__(self) -> None:
        if self.updated_at < self.created_at:
            raise DataSourceTimestampOrderError()
        if self.is_remote and self.dsn is None:
            raise DataSourceRemoteDsnRequiredError()

    def touch(self, changed_at: datetime | None = None) -> None:
        self.updated_at = changed_at or datetime.now(UTC)

    def set_dsn(self, dsn: DataSourceDsnVO | str | None) -> None:
        self.dsn = DataSourceDsnVO.from_value(dsn) if dsn is not None else None
        if self.is_remote and self.dsn is None:
            raise DataSourceRemoteDsnRequiredError()
        self.touch()
