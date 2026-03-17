from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.crm.domain.entities import CompanyEntity, ContactEntity
from src.modules.crm.domain.repositories import (
    CompanyRepositoryProtocol,
    ContactRepositoryProtocol,
)
from src.modules.runtime_record.domain.errors import RuntimeRecordNotFoundError
from src.modules.runtime_record.infrastructure.runtime_value_repository import (
    SqlAlchemyRuntimeValueRepository,
)


class SqlAlchemyContactRepository(ContactRepositoryProtocol):
    def __init__(
        self,
        session: AsyncSession,
        *,
        schema_name: str | None = None,
    ) -> None:
        self._schema_name = schema_name
        self._runtime_values = SqlAlchemyRuntimeValueRepository(session)

    async def add(self, contact: ContactEntity) -> None:
        await self._runtime_values.create_record(
            schema_name=self._schema_name,
            table_name="contacts",
            values={
                "id": str(contact.id),
                "created_at": contact.created_at,
                "updated_at": contact.updated_at,
                "last_name": contact.last_name,
                "first_name": contact.first_name,
                "middle_name": contact.middle_name,
            },
        )

    async def update(self, contact: ContactEntity) -> None:
        await self._runtime_values.write_values(
            schema_name=self._schema_name,
            table_name="contacts",
            record_id=contact.id,
            values={
                "updated_at": contact.updated_at,
                "last_name": contact.last_name,
                "first_name": contact.first_name,
                "middle_name": contact.middle_name,
            },
        )

    async def get_by_id(self, contact_id: UUID) -> ContactEntity | None:
        try:
            values = await self._runtime_values.read_values(
                schema_name=self._schema_name,
                table_name="contacts",
                record_id=contact_id,
                field_names=_CONTACT_FIELDS,
            )
        except RuntimeRecordNotFoundError:
            return None

        return ContactEntity(
            id=_parse_uuid(values["id"]),
            created_at=_parse_datetime(values["created_at"]),
            updated_at=_parse_datetime(values["updated_at"]),
            last_name=str(values["last_name"]),
            first_name=str(values["first_name"]),
            middle_name=(
                str(values["middle_name"]) if values["middle_name"] is not None else None
            ),
        )

    async def list(self) -> tuple[ContactEntity, ...]:
        items = await self._runtime_values.list_values(
            schema_name=self._schema_name,
            table_name="contacts",
            field_names=_CONTACT_FIELDS,
        )
        return tuple(
            ContactEntity(
                id=_parse_uuid(item["id"]),
                created_at=_parse_datetime(item["created_at"]),
                updated_at=_parse_datetime(item["updated_at"]),
                last_name=str(item["last_name"]),
                first_name=str(item["first_name"]),
                middle_name=(
                    str(item["middle_name"]) if item["middle_name"] is not None else None
                ),
            )
            for item in items
        )

    async def delete_by_id(self, contact_id: UUID) -> bool:
        return await self._runtime_values.delete_record(
            schema_name=self._schema_name,
            table_name="contacts",
            record_id=contact_id,
        )


class SqlAlchemyCompanyRepository(CompanyRepositoryProtocol):
    def __init__(
        self,
        session: AsyncSession,
        *,
        schema_name: str | None = None,
    ) -> None:
        self._schema_name = schema_name
        self._runtime_values = SqlAlchemyRuntimeValueRepository(session)

    async def add(self, company: CompanyEntity) -> None:
        await self._runtime_values.create_record(
            schema_name=self._schema_name,
            table_name="companies",
            values={
                "id": str(company.id),
                "created_at": company.created_at,
                "updated_at": company.updated_at,
                "last_name": company.last_name,
                "company_name": company.company_name,
            },
        )

    async def update(self, company: CompanyEntity) -> None:
        await self._runtime_values.write_values(
            schema_name=self._schema_name,
            table_name="companies",
            record_id=company.id,
            values={
                "updated_at": company.updated_at,
                "last_name": company.last_name,
                "company_name": company.company_name,
            },
        )

    async def get_by_id(self, company_id: UUID) -> CompanyEntity | None:
        try:
            values = await self._runtime_values.read_values(
                schema_name=self._schema_name,
                table_name="companies",
                record_id=company_id,
                field_names=_COMPANY_FIELDS,
            )
        except RuntimeRecordNotFoundError:
            return None

        return CompanyEntity(
            id=_parse_uuid(values["id"]),
            created_at=_parse_datetime(values["created_at"]),
            updated_at=_parse_datetime(values["updated_at"]),
            last_name=str(values["last_name"]),
            company_name=str(values["company_name"]),
        )

    async def list(self) -> tuple[CompanyEntity, ...]:
        items = await self._runtime_values.list_values(
            schema_name=self._schema_name,
            table_name="companies",
            field_names=_COMPANY_FIELDS,
        )
        return tuple(
            CompanyEntity(
                id=_parse_uuid(item["id"]),
                created_at=_parse_datetime(item["created_at"]),
                updated_at=_parse_datetime(item["updated_at"]),
                last_name=str(item["last_name"]),
                company_name=str(item["company_name"]),
            )
            for item in items
        )

    async def delete_by_id(self, company_id: UUID) -> bool:
        return await self._runtime_values.delete_record(
            schema_name=self._schema_name,
            table_name="companies",
            record_id=company_id,
        )


def _parse_uuid(value: object) -> UUID:
    if isinstance(value, UUID):
        return value
    return UUID(str(value))


def _parse_datetime(value: object) -> datetime:
    if isinstance(value, datetime):
        return value

    normalized = str(value).strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    if " " in normalized and "T" not in normalized:
        normalized = normalized.replace(" ", "T", 1)

    return datetime.fromisoformat(normalized)


_CONTACT_FIELDS: tuple[str, ...] = (
    "id",
    "created_at",
    "updated_at",
    "last_name",
    "first_name",
    "middle_name",
)

_COMPANY_FIELDS: tuple[str, ...] = (
    "id",
    "created_at",
    "updated_at",
    "last_name",
    "company_name",
)


__all__ = [
    "SqlAlchemyCompanyRepository",
    "SqlAlchemyContactRepository",
]
