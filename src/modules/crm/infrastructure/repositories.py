from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.crm.domain.entities import CompanyEntity, ContactEntity
from src.modules.crm.domain.repositories import (
    CompanyRepositoryProtocol,
    ContactRepositoryProtocol,
)
from src.modules.crm.infrastructure.mappers import (
    company_model_to_entity,
    company_to_model,
    contact_model_to_entity,
    contact_to_model,
)
from src.modules.crm.infrastructure.persistence import CompanyModel, ContactModel


class SqlAlchemyContactRepository(ContactRepositoryProtocol):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def add(self, contact: ContactEntity) -> None:
        self._session.add(contact_to_model(contact))
        await self._session.flush()

    async def update(self, contact: ContactEntity) -> None:
        model = await self._session.scalar(
            select(ContactModel).where(ContactModel.id == str(contact.id))
        )
        if model is None:
            return

        model.updated_at = contact.updated_at
        model.last_name = contact.last_name
        model.first_name = contact.first_name
        model.middle_name = contact.middle_name
        await self._session.flush()

    async def get_by_id(self, contact_id: UUID) -> ContactEntity | None:
        model = await self._session.scalar(
            select(ContactModel).where(ContactModel.id == str(contact_id))
        )
        if model is None:
            return None
        return contact_model_to_entity(model)


class SqlAlchemyCompanyRepository(CompanyRepositoryProtocol):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def add(self, company: CompanyEntity) -> None:
        self._session.add(company_to_model(company))
        await self._session.flush()

    async def update(self, company: CompanyEntity) -> None:
        model = await self._session.scalar(
            select(CompanyModel).where(CompanyModel.id == str(company.id))
        )
        if model is None:
            return

        model.updated_at = company.updated_at
        model.last_name = company.last_name
        model.company_name = company.company_name
        await self._session.flush()

    async def get_by_id(self, company_id: UUID) -> CompanyEntity | None:
        model = await self._session.scalar(
            select(CompanyModel).where(CompanyModel.id == str(company_id))
        )
        if model is None:
            return None
        return company_model_to_entity(model)


__all__ = [
    "SqlAlchemyCompanyRepository",
    "SqlAlchemyContactRepository",
]
