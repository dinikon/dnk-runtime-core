from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.custom_object.application.ports import (
    CustomObjectRecord,
    CustomObjectRecordRepositoryPort,
    GetCustomObjectRecordQuery,
)
from src.modules.custom_object.application.services import CustomObjectRuntimeRecordMapper
from src.modules.custom_object.domain import (
    CustomObjectDataSourceNotFoundError,
    CustomObjectNameVO,
    CustomObjectNotFoundError,
)
from src.modules.runtime_record.application.contracts import GetRuntimeRecordQuery
from src.modules.runtime_record.application.ports import RuntimeRecordReaderPort
from src.modules.runtime_schema.domain.source.value_object import DataSourceIdVO
from src.modules.runtime_schema.infrastructure.repositories import (
    SqlAlchemyObjectMetadataRepository,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.tenancy.infrastructure.persistence.data_source import (
    TenantDataSourceModel,
)


class RuntimeRecordCustomObjectRepository(CustomObjectRecordRepositoryPort):
    def __init__(
        self,
        *,
        session: AsyncSession,
        runtime_record_reader: RuntimeRecordReaderPort,
        mapper: CustomObjectRuntimeRecordMapper,
    ):
        self._session = session
        self._runtime_record_reader = runtime_record_reader
        self._mapper = mapper
        self._object_repository = SqlAlchemyObjectMetadataRepository(session)

    async def get_by_id(
        self,
        query: GetCustomObjectRecordQuery,
    ) -> CustomObjectRecord | None:
        object_name = CustomObjectNameVO(query.object_name_singular)
        data_source_model = await self._resolve_data_source(query.tenant_id)
        object_entity = await self._object_repository.get_by_name(
            tenant_id=EntityIdVO.from_value(query.tenant_id),
            data_source_id=DataSourceIdVO.from_value(data_source_model.id),
            object_name_singular=object_name.value,
        )
        if object_entity is None or not object_entity.is_active:
            raise CustomObjectNotFoundError(object_name.value)
        if object_entity.is_system or not object_entity.is_custom:
            raise CustomObjectNotFoundError(object_name.value)

        payload = await self._runtime_record_reader.get_record(
            GetRuntimeRecordQuery(
                tenant_id=query.tenant_id,
                object_name_singular=object_name.value,
                record_id=query.record_id,
            )
        )
        if payload is None:
            return None
        return CustomObjectRecord(record=self._mapper.map_payload(payload))

    async def _resolve_data_source(self, tenant_id: UUID) -> TenantDataSourceModel:
        data_source_model = await self._session.scalar(
            select(TenantDataSourceModel)
            .where(TenantDataSourceModel.tenant_id == str(tenant_id))
            .limit(1)
        )
        if data_source_model is None:
            raise CustomObjectDataSourceNotFoundError(str(tenant_id))
        return data_source_model


__all__ = ["RuntimeRecordCustomObjectRepository"]
