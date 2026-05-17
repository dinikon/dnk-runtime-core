from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any
from uuid import UUID

from src.modules.crm.application.company.dto import CompanyDTO
from src.modules.crm.application.company.query.repository import (
    CompanyQueryRepositoryProtocol,
)
from src.modules.crm.domain.company.entity import CompanyEntity
from src.modules.crm.domain.company.error import CompanyNotFoundError
from src.modules.crm.domain.company.repository import CompanyCommandRepositoryProtocol
from src.modules.crm.domain.company.value_object import (
    CompanyIdVO,
    CompanyLegalNameVO,
)
from src.modules.runtime_data.application.models import PageSpec, SortSpec
from src.modules.runtime_data.application.ports import (
    RuntimeCommandGateway,
    RuntimeQueryGateway,
)
from src.modules.schema_registry.runtime import RuntimeObjectResolverProtocol
from src.modules.shared import EntityIdVO


class CompanyRuntimeRepository(
    CompanyCommandRepositoryProtocol,
    CompanyQueryRepositoryProtocol,
):
    """CRM-репозиторий компаний поверх runtime_data gateway и descriptor resolver."""

    _OBJECT_NAME = "company"

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
        company_id: CompanyIdVO,
    ) -> CompanyEntity | None:
        """Загружает доменную entity компании из runtime-таблицы tenant."""
        descriptor = await self._resolve_descriptor(tenant_id)
        row = await self._runtime_query_gateway.get_by_id(
            descriptor=descriptor,
            object_id=company_id.uuid,
        )
        if row is None:
            return None
        return self._row_to_entity(row)

    async def save(
        self,
        *,
        tenant_id: EntityIdVO,
        company: CompanyEntity,
    ) -> CompanyEntity:
        """Создает или обновляет runtime-строку компании и возвращает entity."""
        descriptor = await self._resolve_descriptor(tenant_id)
        existing = await self._runtime_query_gateway.get_by_id(
            descriptor=descriptor,
            object_id=company.id.uuid,
        )
        payload = {
            "legal_name": company.legal_name.value,
        }

        if existing is None:
            row = await self._runtime_command_gateway.insert(
                descriptor=descriptor,
                payload={
                    "id": company.id.uuid,
                    **payload,
                },
            )
        else:
            row = await self._runtime_command_gateway.update(
                descriptor=descriptor,
                object_id=company.id.uuid,
                patch=payload,
            )
            if row is None:
                raise CompanyNotFoundError(str(company.id))

        return self._row_to_entity(row)

    async def delete(
        self,
        *,
        tenant_id: EntityIdVO,
        company_id: CompanyIdVO,
    ) -> None:
        """Удаляет runtime-строку компании или поднимает not-found ошибку."""
        descriptor = await self._resolve_descriptor(tenant_id)
        deleted = await self._runtime_command_gateway.delete(
            descriptor=descriptor,
            object_id=company_id.uuid,
        )
        if not deleted:
            raise CompanyNotFoundError(str(company_id))

    async def get_by_id(
        self,
        *,
        tenant_id: EntityIdVO,
        company_id: CompanyIdVO,
    ) -> CompanyDTO | None:
        """Возвращает CompanyDTO по id для query-сценариев."""
        descriptor = await self._resolve_descriptor(tenant_id)
        row = await self._runtime_query_gateway.get_by_id(
            descriptor=descriptor,
            object_id=company_id.uuid,
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
    ) -> list[CompanyDTO]:
        """Возвращает страницу CompanyDTO, сортируя runtime-строки стабильно."""
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
        """Получает runtime descriptor CRM-объекта company для tenant."""
        return await self._runtime_object_resolver.resolve(
            tenant_id=tenant_id,
            object_name=self._OBJECT_NAME,
        )

    @staticmethod
    def _row_to_entity(row: Mapping[str, Any]) -> CompanyEntity:
        """Мапит runtime row в доменную CompanyEntity с проверкой типов."""
        return CompanyEntity(
            id=CompanyIdVO.from_value(CompanyRuntimeRepository._as_uuid(row.get("id"))),
            created_at=CompanyRuntimeRepository._as_datetime(row.get("created_at")),
            updated_at=CompanyRuntimeRepository._as_datetime(row.get("updated_at")),
            legal_name=CompanyLegalNameVO(
                CompanyRuntimeRepository._as_str(row.get("legal_name"))
            ),
        )

    @staticmethod
    def _row_to_dto(row: Mapping[str, Any]) -> CompanyDTO:
        """Мапит runtime row в CompanyDTO с проверкой типов."""
        return CompanyDTO(
            id=CompanyRuntimeRepository._as_uuid(row.get("id")),
            created_at=CompanyRuntimeRepository._as_datetime(row.get("created_at")),
            updated_at=CompanyRuntimeRepository._as_datetime(row.get("updated_at")),
            legal_name=CompanyRuntimeRepository._as_str(row.get("legal_name")),
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
