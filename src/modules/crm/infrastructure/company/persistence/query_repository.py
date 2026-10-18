from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.crm.application.company.query.get_company.dto import CompanyDetailsDTO
from src.modules.crm.domain.company.value_object.identifier import CompanyIdVO
from src.modules.crm.infrastructure.company.persistence.query_mapper import (
    CompanyQueryMapper,
)
from src.modules.crm.infrastructure.persistence.models.company import CompanyModel


class SqlAlchemyCompanyQueryRepository:
    """Чтение проекций компании без блокировки и восстановления агрегата."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @staticmethod
    def _details_select():
        return select(
            CompanyModel.id.label("id"),
            CompanyModel.legal_name.label("legal_name"),
            CompanyModel.created_at.label("created_at"),
            CompanyModel.updated_at.label("updated_at"),
            CompanyModel.created_by.label("created_by"),
            CompanyModel.updated_by.label("updated_by"),
        )

    async def get_details(self, *, company_id: CompanyIdVO) -> CompanyDetailsDTO | None:
        result = await self._session.execute(
            self._details_select().where(CompanyModel.id == company_id.uuid)
        )
        row = result.mappings().one_or_none()
        return None if row is None else CompanyQueryMapper.to_details(row)

    async def list_details(self) -> list[CompanyDetailsDTO]:
        result = await self._session.execute(
            self._details_select().order_by(CompanyModel.created_at, CompanyModel.id)
        )
        return [CompanyQueryMapper.to_details(row) for row in result.mappings().all()]
