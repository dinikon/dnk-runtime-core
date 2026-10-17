from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.crm.domain.company.value_object.identifier import CompanyIdVO
from src.modules.crm.domain.contact.value_object.company_link import (
    ContactCompanyLinkVO,
)
from src.modules.crm.domain.contact.value_object.identifier import ContactIdVO
from src.modules.crm.infrastructure.persistence.models.company import CompanyModel
from src.modules.crm.infrastructure.persistence.models.contact import ContactModel
from src.modules.crm.infrastructure.persistence.models.contact_company import (
    ContactCompanyModel,
)


class SqlAlchemyCompanyLinkRepository:
    """Пишет одну связь в сессии уже выбранного tenant."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def lock_contact(self, contact_id: ContactIdVO) -> bool:
        result = await self._session.execute(
            select(ContactModel.id)
            .where(ContactModel.id == contact_id.uuid)
            .with_for_update(read=True, key_share=True)
        )
        return result.scalar_one_or_none() is not None

    async def lock_company(self, company_id: CompanyIdVO) -> bool:
        result = await self._session.execute(
            select(CompanyModel.id)
            .where(CompanyModel.id == company_id.uuid)
            .with_for_update(read=True, key_share=True)
        )
        return result.scalar_one_or_none() is not None

    async def link(self, link: ContactCompanyLinkVO) -> None:
        await self._session.execute(
            pg_insert(ContactCompanyModel)
            .values(contact_id=link.contact_id.uuid, company_id=link.company_id.uuid)
            .on_conflict_do_nothing(
                index_elements=[
                    ContactCompanyModel.contact_id,
                    ContactCompanyModel.company_id,
                ]
            )
        )

    async def unlink(self, link: ContactCompanyLinkVO) -> None:
        await self._session.execute(
            delete(ContactCompanyModel).where(
                ContactCompanyModel.contact_id == link.contact_id.uuid,
                ContactCompanyModel.company_id == link.company_id.uuid,
            )
        )
