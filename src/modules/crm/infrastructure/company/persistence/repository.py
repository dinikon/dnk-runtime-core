from sqlalchemy import delete, insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.crm.domain.company.aggregate import CompanyEntity
from src.modules.crm.domain.company.value_object.identifier import CompanyIdVO
from src.modules.crm.infrastructure.company.persistence.mapper import CompanyMapper
from src.modules.crm.infrastructure.persistence.models.company import CompanyModel


class SqlAlchemyCompanyRepository:
    """Запись в tenant-схему через общую сессию внешнего UoW."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, company: CompanyEntity) -> None:
        await self._session.execute(
            insert(CompanyModel).values(CompanyMapper.to_insert_values(company))
        )

    async def get_for_update(self, company_id: CompanyIdVO) -> CompanyEntity | None:
        result = await self._session.execute(
            select(
                CompanyModel.id.label("id"),
                CompanyModel.legal_name.label("legal_name"),
                CompanyModel.created_at.label("created_at"),
                CompanyModel.updated_at.label("updated_at"),
                CompanyModel.created_by.label("created_by"),
                CompanyModel.updated_by.label("updated_by"),
            )
            .where(CompanyModel.id == company_id.uuid)
            .with_for_update()
        )
        row = result.mappings().one_or_none()
        return None if row is None else CompanyMapper.to_entity(row)

    async def save(self, company: CompanyEntity) -> None:
        await self._session.execute(
            update(CompanyModel)
            .where(CompanyModel.id == company.id.uuid)
            .values(CompanyMapper.to_update_values(company))
        )

    async def delete(self, company: CompanyEntity) -> None:
        await self._session.execute(
            delete(CompanyModel).where(CompanyModel.id == company.id.uuid)
        )
