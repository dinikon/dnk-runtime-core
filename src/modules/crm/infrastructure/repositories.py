from __future__ import annotations

from datetime import datetime
from re import Pattern, compile as re_compile
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.crm.domain.entities import CompanyEntity, ContactEntity
from src.modules.crm.domain.repositories import (
    CompanyRepositoryProtocol,
    ContactRepositoryProtocol,
)

_IDENTIFIER_PATTERN: Pattern[str] = re_compile(r"^[a-z_][a-z0-9_]{0,62}$")
_SCHEMA_PATTERN: Pattern[str] = re_compile(r"^[A-Za-z0-9_-]{1,128}$")


class SqlAlchemyContactRepository(ContactRepositoryProtocol):
    def __init__(
        self,
        session: AsyncSession,
        *,
        schema_name: str | None = None,
    ) -> None:
        self._session = session
        self._schema_name = schema_name

    async def add(self, contact: ContactEntity) -> None:
        table_ref = _qualified_table(
            session=self._session,
            schema_name=self._schema_name,
            table_name="contacts",
        )
        await self._session.execute(
            text(
                f"INSERT INTO {table_ref} "
                "(id, created_at, updated_at, last_name, first_name, middle_name) "
                "VALUES (:id, :created_at, :updated_at, :last_name, :first_name, :middle_name)"
            ),
            {
                "id": str(contact.id),
                "created_at": contact.created_at,
                "updated_at": contact.updated_at,
                "last_name": contact.last_name,
                "first_name": contact.first_name,
                "middle_name": contact.middle_name,
            },
        )
        await self._session.flush()

    async def update(self, contact: ContactEntity) -> None:
        table_ref = _qualified_table(
            session=self._session,
            schema_name=self._schema_name,
            table_name="contacts",
        )
        await self._session.execute(
            text(
                f"UPDATE {table_ref} "
                "SET updated_at = :updated_at, "
                "last_name = :last_name, "
                "first_name = :first_name, "
                "middle_name = :middle_name "
                "WHERE id = :id"
            ),
            {
                "id": str(contact.id),
                "updated_at": contact.updated_at,
                "last_name": contact.last_name,
                "first_name": contact.first_name,
                "middle_name": contact.middle_name,
            },
        )
        await self._session.flush()

    async def get_by_id(self, contact_id: UUID) -> ContactEntity | None:
        table_ref = _qualified_table(
            session=self._session,
            schema_name=self._schema_name,
            table_name="contacts",
        )
        rows = await self._session.execute(
            text(
                f"SELECT id, created_at, updated_at, last_name, first_name, middle_name "
                f"FROM {table_ref} "
                "WHERE id = :id"
            ),
            {"id": str(contact_id)},
        )
        row = rows.first()
        if row is None:
            return None

        return ContactEntity(
            id=_parse_uuid(row[0]),
            created_at=_parse_datetime(row[1]),
            updated_at=_parse_datetime(row[2]),
            last_name=str(row[3]),
            first_name=str(row[4]),
            middle_name=str(row[5]) if row[5] is not None else None,
        )


class SqlAlchemyCompanyRepository(CompanyRepositoryProtocol):
    def __init__(
        self,
        session: AsyncSession,
        *,
        schema_name: str | None = None,
    ) -> None:
        self._session = session
        self._schema_name = schema_name

    async def add(self, company: CompanyEntity) -> None:
        table_ref = _qualified_table(
            session=self._session,
            schema_name=self._schema_name,
            table_name="companies",
        )
        await self._session.execute(
            text(
                f"INSERT INTO {table_ref} "
                "(id, created_at, updated_at, last_name, company_name) "
                "VALUES (:id, :created_at, :updated_at, :last_name, :company_name)"
            ),
            {
                "id": str(company.id),
                "created_at": company.created_at,
                "updated_at": company.updated_at,
                "last_name": company.last_name,
                "company_name": company.company_name,
            },
        )
        await self._session.flush()

    async def update(self, company: CompanyEntity) -> None:
        table_ref = _qualified_table(
            session=self._session,
            schema_name=self._schema_name,
            table_name="companies",
        )
        await self._session.execute(
            text(
                f"UPDATE {table_ref} "
                "SET updated_at = :updated_at, "
                "last_name = :last_name, "
                "company_name = :company_name "
                "WHERE id = :id"
            ),
            {
                "id": str(company.id),
                "updated_at": company.updated_at,
                "last_name": company.last_name,
                "company_name": company.company_name,
            },
        )
        await self._session.flush()

    async def get_by_id(self, company_id: UUID) -> CompanyEntity | None:
        table_ref = _qualified_table(
            session=self._session,
            schema_name=self._schema_name,
            table_name="companies",
        )
        rows = await self._session.execute(
            text(
                f"SELECT id, created_at, updated_at, last_name, company_name "
                f"FROM {table_ref} "
                "WHERE id = :id"
            ),
            {"id": str(company_id)},
        )
        row = rows.first()
        if row is None:
            return None

        return CompanyEntity(
            id=_parse_uuid(row[0]),
            created_at=_parse_datetime(row[1]),
            updated_at=_parse_datetime(row[2]),
            last_name=str(row[3]),
            company_name=str(row[4]),
        )


def _qualified_table(
    *,
    session: AsyncSession,
    schema_name: str | None,
    table_name: str,
) -> str:
    quoted_table = _quoted_identifier(table_name)
    dialect_name = session.bind.dialect.name if session.bind else ""

    if not schema_name or dialect_name == "sqlite":
        return quoted_table

    return f"{_quoted_schema_name(schema_name)}.{quoted_table}"


def _quoted_identifier(value: str) -> str:
    normalized = value.strip().lower()
    if not _IDENTIFIER_PATTERN.fullmatch(normalized):
        raise ValueError(f"Invalid SQL identifier: '{value}'")
    return f'"{normalized}"'


def _quoted_schema_name(value: str) -> str:
    normalized = value.strip()
    if not _SCHEMA_PATTERN.fullmatch(normalized):
        raise ValueError(f"Invalid schema name: '{value}'")
    escaped = normalized.replace('"', '""')
    return f'"{escaped}"'


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


__all__ = [
    "SqlAlchemyCompanyRepository",
    "SqlAlchemyContactRepository",
]
