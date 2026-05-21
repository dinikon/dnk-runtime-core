from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any, List
from uuid import UUID

from src.modules.crm.application.contact.dto.contact_dto import ContactDTO
from src.modules.crm.application.contact.query.repository import (
    ContactQueryRepositoryProtocol,
)
from src.modules.crm.domain.contact.entity import ContactEntity
from src.modules.crm.domain.contact.error import ContactNotFoundError
from src.modules.crm.domain.contact.repository import ContactCommandRepositoryProtocol
from src.modules.crm.domain.contact.value_object import ContactIdVO, ContactNameVO
from src.modules.runtime_data.application.models import PageSpec, SortSpec
from src.modules.runtime_data.application.ports import (
    RuntimeCommandGateway,
    RuntimeQueryGateway,
)
from src.modules.schema_registry.runtime import RuntimeObjectResolverProtocol
from src.modules.shared import EntityIdVO


class ContactRuntimeRepository(
    ContactCommandRepositoryProtocol,
    ContactQueryRepositoryProtocol,
):
    """CRM-репозиторий контактов поверх runtime_data gateway и descriptor resolver.

    Адаптер прячет динамическую runtime-схему за доменными/query портами CRM:
    сначала получает descriptor объекта `contact`, затем выполняет CRUD через
    runtime gateways и мапит строки БД в ContactEntity или ContactDTO.
    """

    _OBJECT_NAME = "contact"

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

    async def load(
        self,
        *,
        tenant_id: EntityIdVO,
        contact_id: ContactIdVO,
    ) -> ContactEntity | None:
        """Загружает доменную entity контакта из runtime-таблицы tenant."""
        descriptor = await self._resolve_descriptor(tenant_id)
        row = await self._runtime_query_gateway.get_by_id(
            descriptor=descriptor,
            object_id=contact_id.uuid,
        )
        if row is None:
            return None
        return self._row_to_entity(row)

    async def save(
        self,
        *,
        tenant_id: EntityIdVO,
        contact: ContactEntity,
    ) -> ContactEntity:
        """Создает или обновляет runtime-строку контакта и возвращает entity."""
        descriptor = await self._resolve_descriptor(tenant_id)
        existing = await self._runtime_query_gateway.get_by_id(
            descriptor=descriptor,
            object_id=contact.id.uuid,
        )

        if existing is None:
            payload = {
                "id": contact.id.uuid,
                "last_name": contact.contact_name.last_name,
                "first_name": contact.contact_name.first_name,
                "middle_name": contact.contact_name.middle_name,
                "tags": list(contact.tags),
            }
            if contact.status is not None:
                payload["status"] = contact.status
            row = await self._runtime_command_gateway.insert(
                descriptor=descriptor,
                payload=payload,
            )
        else:
            row = await self._runtime_command_gateway.update(
                descriptor=descriptor,
                object_id=contact.id.uuid,
                patch={
                    "last_name": contact.contact_name.last_name,
                    "first_name": contact.contact_name.first_name,
                    "middle_name": contact.contact_name.middle_name,
                    "status": contact.status,
                    "tags": list(contact.tags),
                },
            )
            if row is None:
                raise ContactNotFoundError(str(contact.id))

        return self._row_to_entity(row)

    async def delete(
        self,
        *,
        tenant_id: EntityIdVO,
        contact_id: ContactIdVO,
    ) -> None:
        """Удаляет runtime-строку контакта или поднимает not-found ошибку."""
        descriptor = await self._resolve_descriptor(tenant_id)
        deleted = await self._runtime_command_gateway.delete(
            descriptor=descriptor,
            object_id=contact_id.uuid,
        )
        if not deleted:
            raise ContactNotFoundError(str(contact_id))

    async def get_by_id(
        self,
        *,
        tenant_id: EntityIdVO,
        contact_id: ContactIdVO,
    ) -> ContactDTO | None:
        """Возвращает ContactDTO по id для query-сценариев."""
        descriptor = await self._resolve_descriptor(tenant_id)
        row = await self._runtime_query_gateway.get_by_id(
            descriptor=descriptor,
            object_id=contact_id.uuid,
        )
        if row is None:
            return None
        return self._row_to_dto(row)

    async def list(
        self,
        *,
        tenant_id: EntityIdVO,
        limit: int,
        offset: int,
    ) -> List[ContactDTO]:
        """Возвращает страницу ContactDTO, сортируя runtime-строки стабильно."""
        descriptor = await self._resolve_descriptor(tenant_id)
        rows = await self._runtime_query_gateway.list(
            descriptor=descriptor,
            sorting=(
                SortSpec(field="created_at", direction="asc"),
                SortSpec(field="id", direction="asc"),
            ),
            page=PageSpec(limit=limit, offset=offset),
        )
        return [self._row_to_dto(row) for row in rows]

    async def _resolve_descriptor(self, tenant_id: EntityIdVO):
        """Получает runtime descriptor CRM-объекта contact для tenant."""
        return await self._runtime_object_resolver.resolve(
            tenant_id=tenant_id,
            object_name=self._OBJECT_NAME,
        )

    @staticmethod
    def _row_to_entity(row: Mapping[str, Any]) -> ContactEntity:
        """Мапит runtime row в доменную ContactEntity с проверкой типов."""
        return ContactEntity(
            id=ContactIdVO.from_value(ContactRuntimeRepository._as_uuid(row.get("id"))),
            created_at=ContactRuntimeRepository._as_datetime(row.get("created_at")),
            updated_at=ContactRuntimeRepository._as_datetime(row.get("updated_at")),
            contact_name=ContactNameVO(
                last_name=ContactRuntimeRepository._as_optional_str(
                    row.get("last_name")
                ),
                first_name=ContactRuntimeRepository._as_str(row.get("first_name")),
                middle_name=ContactRuntimeRepository._as_optional_str(
                    row.get("middle_name")
                ),
            ),
            status=ContactRuntimeRepository._as_optional_str(row.get("status")),
            tags=ContactRuntimeRepository._as_str_list(row.get("tags")),
        )

    @staticmethod
    def _row_to_dto(row: Mapping[str, Any]) -> ContactDTO:
        """Мапит runtime row в ContactDTO с проверкой типов."""
        return ContactDTO(
            id=ContactRuntimeRepository._as_uuid(row.get("id")),
            created_at=ContactRuntimeRepository._as_datetime(row.get("created_at")),
            updated_at=ContactRuntimeRepository._as_datetime(row.get("updated_at")),
            last_name=ContactRuntimeRepository._as_optional_str(row.get("last_name")),
            first_name=ContactRuntimeRepository._as_str(row.get("first_name")),
            middle_name=ContactRuntimeRepository._as_optional_str(
                row.get("middle_name")
            ),
            status=ContactRuntimeRepository._as_optional_str(row.get("status")),
            tags=ContactRuntimeRepository._as_str_list(row.get("tags")),
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

    @staticmethod
    def _as_str_list(value: Any) -> List[str]:
        """Достает список строк из runtime row, трактуя None как пустой список."""
        if value is None:
            return []
        if isinstance(value, list) and all(isinstance(item, str) for item in value):
            return list(value)
        raise TypeError("Runtime row must contain list[str] value.")
