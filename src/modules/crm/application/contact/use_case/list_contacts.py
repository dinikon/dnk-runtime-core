from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any, Protocol
from uuid import UUID

from src.modules.crm.application.contact.dto import ContactDTO, ContactListResultDTO
from src.modules.crm.application.contact.query.list_contacts_query import (
    ListContactsQuery,
)
from src.modules.runtime_data.application.query.query import RuntimeSearchRecordsQuery
from src.modules.runtime_data.application.query.runtime_object_query_service import (
    RuntimeObjectQueryService,
)


class ListContactsUseCaseProtocol(Protocol):
    """Порт use case получения списка контактов."""

    async def __call__(self, query: ListContactsQuery) -> ContactListResultDTO:
        """Возвращает страницу контактов tenant."""
        ...


class ListContactsUseCase:
    """Use case чтения списка CRM-контактов через runtime query service."""

    _OBJECT_NAME = "contact"

    def __init__(self, runtime_query_service: RuntimeObjectQueryService):
        """Инициализирует use case runtime query service."""
        self._runtime_query_service = runtime_query_service

    async def __call__(self, query: ListContactsQuery) -> ContactListResultDTO:
        """Выполняет query списка контактов."""
        runtime_result = await self._runtime_query_service.search_records(
            RuntimeSearchRecordsQuery(
                tenant_id=query.tenant_id,
                object_name=self._OBJECT_NAME,
                filter_dsl=query.filter_dsl,
                sort_dsl=query.sort_dsl,
                limit=query.limit,
                offset=query.offset,
            )
        )
        return ContactListResultDTO(
            items=tuple(self._row_to_dto(row.values) for row in runtime_result.rows),
            total=runtime_result.total,
            limit=query.limit,
            offset=query.offset,
        )

    @staticmethod
    def _row_to_dto(row: Mapping[str, Any]) -> ContactDTO:
        return ContactDTO(
            id=ListContactsUseCase._as_uuid(row.get("id")),
            created_at=ListContactsUseCase._as_datetime(row.get("created_at")),
            updated_at=ListContactsUseCase._as_datetime(row.get("updated_at")),
            last_name=ListContactsUseCase._as_optional_str(row.get("last_name")),
            first_name=ListContactsUseCase._as_str(row.get("first_name")),
            middle_name=ListContactsUseCase._as_optional_str(row.get("middle_name")),
            status=ListContactsUseCase._as_optional_str(row.get("status")),
            tags=ListContactsUseCase._as_str_list(row.get("tags")),
        )

    @staticmethod
    def _as_uuid(value: Any) -> UUID:
        if isinstance(value, UUID):
            return value
        if isinstance(value, str):
            return UUID(value)
        raise TypeError("Runtime row must contain UUID value.")

    @staticmethod
    def _as_datetime(value: Any) -> datetime:
        if isinstance(value, datetime):
            return value
        raise TypeError("Runtime row must contain datetime value.")

    @staticmethod
    def _as_str(value: Any) -> str:
        if isinstance(value, str):
            return value
        raise TypeError("Runtime row must contain string value.")

    @staticmethod
    def _as_optional_str(value: Any) -> str | None:
        if value is None:
            return None
        if isinstance(value, str):
            return value
        raise TypeError("Runtime row must contain optional string value.")

    @staticmethod
    def _as_str_list(value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, list) and all(isinstance(item, str) for item in value):
            return list(value)
        raise TypeError("Runtime row must contain list[str] value.")
