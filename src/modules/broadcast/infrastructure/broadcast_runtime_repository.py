from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Any
from uuid import UUID

from src.modules.broadcast.application.broadcast.dto import BroadcastDTO
from src.modules.broadcast.application.broadcast.dto import BroadcastListDTO
from src.modules.broadcast.application.broadcast.repository import (
    BroadcastCommandRepositoryProtocol,
    BroadcastQueryRepositoryProtocol,
)
from src.modules.broadcast.domain.broadcast.entity import BroadcastEntity
from src.modules.broadcast.domain.broadcast.value_object.broadcast_id import (
    BroadcastIdVO,
)
from src.modules.broadcast.domain.broadcast.value_object.broadcast_status import (
    BroadcastStatusVO,
)
from src.modules.runtime_data.application.ports import (
    RuntimeCommandGateway,
    RuntimeQueryGateway,
)
from src.modules.runtime_data.application.query.query import RuntimeSearchRecordsQuery
from src.modules.runtime_data.application.query.runtime_object_query_service import (
    RuntimeObjectQueryService,
)
from src.modules.schema_registry.runtime import RuntimeObjectResolverProtocol
from src.modules.shared import EntityIdVO
from src.modules.shared.domain.value_object.entity_description import (
    EntityDescriptionVO,
)
from src.modules.shared.domain.value_object.entity_title import EntityTitleVO


class BroadcastRuntimeRepository(
    BroadcastCommandRepositoryProtocol,
    BroadcastQueryRepositoryProtocol,
):
    """Broadcast repository поверх runtime_data gateway."""

    _OBJECT_NAME = "broadcast"

    def __init__(
        self,
        runtime_object_resolver: RuntimeObjectResolverProtocol,
        runtime_command_gateway: RuntimeCommandGateway,
        runtime_query_gateway: RuntimeQueryGateway,
    ) -> None:
        """Инициализирует repository resolver-ом descriptor и runtime gateways."""
        self._runtime_object_resolver = runtime_object_resolver
        self._runtime_command_gateway = runtime_command_gateway
        self._runtime_query_gateway = runtime_query_gateway
        self._runtime_query_service = RuntimeObjectQueryService(
            runtime_object_resolver=runtime_object_resolver,
            runtime_query_gateway=runtime_query_gateway,
        )

    async def load(
        self,
        *,
        tenant_id: EntityIdVO,
        broadcast_id: BroadcastIdVO,
    ) -> BroadcastEntity | None:
        """Загружает доменную entity broadcast из runtime-таблицы tenant."""
        descriptor = await self._resolve_descriptor(tenant_id)
        row = await self._runtime_query_gateway.get_by_id(
            descriptor=descriptor,
            object_id=broadcast_id.uuid,
        )
        if row is None:
            return None
        return self._row_to_entity(row)

    async def list(
        self,
        *,
        tenant_id: EntityIdVO,
        filter_dsl: Mapping[str, Any] | None,
        sort_dsl: Sequence[Mapping[str, Any]],
        limit: int,
        offset: int,
    ) -> BroadcastListDTO:
        """Возвращает страницу broadcast definitions через runtime search."""
        result = await self._runtime_query_service.search_records(
            RuntimeSearchRecordsQuery(
                tenant_id=tenant_id,
                object_name=self._OBJECT_NAME,
                filter_dsl=filter_dsl,
                sort_dsl=sort_dsl,
                limit=limit,
                offset=offset,
            )
        )
        return BroadcastListDTO(
            items=tuple(
                self._entity_to_dto(self._row_to_entity(row.values))
                for row in result.rows
            ),
            total=result.total,
            limit=result.limit,
            offset=result.offset,
        )

    async def get(
        self,
        *,
        tenant_id: EntityIdVO,
        broadcast_id: BroadcastIdVO,
    ) -> BroadcastDTO | None:
        """Возвращает одну broadcast definition через runtime get_by_id."""
        descriptor = await self._resolve_descriptor(tenant_id)
        row = await self._runtime_query_gateway.get_by_id(
            descriptor=descriptor,
            object_id=broadcast_id.uuid,
        )
        if row is None:
            return None
        return self._entity_to_dto(self._row_to_entity(row))

    async def save(
        self,
        *,
        tenant_id: EntityIdVO,
        broadcast: BroadcastEntity,
    ) -> BroadcastEntity:
        """Создает или обновляет runtime-строку broadcast и возвращает entity."""
        descriptor = await self._resolve_descriptor(tenant_id)
        existing = await self._runtime_query_gateway.get_by_id(
            descriptor=descriptor,
            object_id=broadcast.id.uuid,
        )
        payload = {
            "title": broadcast.title.value,
            "description": (
                None if broadcast.description is None else broadcast.description.value
            ),
            "status": broadcast.status.value,
        }

        if existing is None:
            row = await self._runtime_command_gateway.insert(
                descriptor=descriptor,
                payload={
                    "id": broadcast.id.uuid,
                    **payload,
                },
            )
        else:
            row = await self._runtime_command_gateway.update(
                descriptor=descriptor,
                object_id=broadcast.id.uuid,
                patch=payload,
            )
            if row is None:
                raise LookupError(str(broadcast.id))

        return self._row_to_entity(row)

    async def _resolve_descriptor(self, tenant_id: EntityIdVO):
        """Получает runtime descriptor объекта broadcast для tenant."""
        return await self._runtime_object_resolver.resolve(
            tenant_id=tenant_id,
            object_name=self._OBJECT_NAME,
        )

    @staticmethod
    def _row_to_entity(row: Mapping[str, Any]) -> BroadcastEntity:
        """Мапит runtime row в доменную BroadcastEntity с проверкой типов."""
        description = BroadcastRuntimeRepository._as_optional_str(
            row.get("description")
        )
        return BroadcastEntity(
            id=BroadcastIdVO.from_value(
                BroadcastRuntimeRepository._as_uuid(row.get("id"))
            ),
            created_at=BroadcastRuntimeRepository._as_datetime(row.get("created_at")),
            updated_at=BroadcastRuntimeRepository._as_datetime(row.get("updated_at")),
            title=EntityTitleVO(BroadcastRuntimeRepository._as_str(row.get("title"))),
            description=(
                None if description is None else EntityDescriptionVO(description)
            ),
            status=BroadcastStatusVO(
                BroadcastRuntimeRepository._as_str(row.get("status"))
            ),
        )

    @staticmethod
    def _entity_to_dto(broadcast: BroadcastEntity) -> BroadcastDTO:
        """Мапит BroadcastEntity в DTO ответа."""
        return BroadcastDTO(
            id=broadcast.id.uuid,
            created_at=broadcast.created_at,
            updated_at=broadcast.updated_at,
            title=broadcast.title.value,
            description=(
                None if broadcast.description is None else broadcast.description.value
            ),
            status=broadcast.status.value,
        )

    @staticmethod
    def _as_uuid(value: Any) -> UUID:
        """Достает UUID из runtime row или поднимает TypeError."""
        if isinstance(value, UUID):
            return value
        if isinstance(value, str):
            return UUID(value)
        raise TypeError("Runtime row must contain UUID value.")

    @staticmethod
    def _as_datetime(value: Any) -> datetime:
        """Достает datetime из runtime row или поднимает TypeError."""
        if isinstance(value, datetime):
            return value
        raise TypeError("Runtime row must contain datetime value.")

    @staticmethod
    def _as_str(value: Any) -> str:
        """Достает обязательную строку из runtime row."""
        if isinstance(value, str):
            return value
        raise TypeError("Runtime row must contain string value.")

    @staticmethod
    def _as_optional_str(value: Any) -> str | None:
        """Достает optional строку из runtime row."""
        if value is None:
            return None
        if isinstance(value, str):
            return value
        raise TypeError("Runtime row must contain optional string value.")


__all__ = ["BroadcastRuntimeRepository"]
