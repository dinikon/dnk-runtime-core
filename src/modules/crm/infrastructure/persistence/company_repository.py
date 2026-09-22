from datetime import datetime

from sqlalchemy import delete, func, insert, select, update

from src.modules.crm.application.company.dto import CompanyPageDTO, company_dto
from src.modules.crm.application.company.query import ListCompaniesQuery
from src.modules.crm.domain.company import (
    Company,
    CompanyIdVO,
    CompanyNameVO,
    CompanyNotFoundError,
)
from src.modules.crm.infrastructure.persistence.base import (
    CrmSessionRepository,
    checked,
    identifier,
)
from src.modules.crm.infrastructure.persistence.models import CompanyModel


def company_entity(row) -> Company:
    """Явно мапит persistence row в Company aggregate."""
    return Company(
        id=identifier(row["id"], CompanyIdVO),
        name=CompanyNameVO(checked(row["name"], str)),
        created_at=checked(row["created_at"], datetime),
        updated_at=checked(row["updated_at"], datetime),
        created_by=identifier(row["created_by"]),
        updated_by=identifier(row["updated_by"]),
    )


def company_values(company: Company) -> dict[str, object]:
    """Преобразует Company aggregate в persistence primitives."""
    return {
        "id": company.id.uuid,
        "name": company.name.value,
        "created_at": company.created_at,
        "updated_at": company.updated_at,
        "created_by": company.created_by.uuid,
        "updated_by": company.updated_by.uuid,
    }


class SqlAlchemyCompanyRepository(CrmSessionRepository):
    """Реализует command/query CRM company repositories через SQLAlchemy."""

    async def get(self, tenant_id, company_id, *, for_update=False):
        """Читает одну компанию текущего tenant."""
        table = CompanyModel.__table__
        statement = select(table).where(table.c.id == company_id.uuid)
        if for_update:
            statement = statement.with_for_update()
        result = await self.session.execute(
            statement.execution_options(**self.execution_options(tenant_id))
        )
        row = result.mappings().one_or_none()
        if row is None:
            raise CompanyNotFoundError("Company not found.")
        return company_entity(row)

    async def add(self, tenant_id, company):
        """Добавляет компанию в tenant-схему."""
        await self.session.execute(
            insert(CompanyModel.__table__)
            .values(company_values(company))
            .execution_options(**self.execution_options(tenant_id))
        )

    async def save(self, tenant_id, company):
        """Сохраняет название и update audit."""
        values = company_values(company)
        values.pop("id")
        values.pop("created_at")
        values.pop("created_by")
        result = await self.session.execute(
            update(CompanyModel.__table__)
            .where(CompanyModel.__table__.c.id == company.id.uuid)
            .values(values)
            .execution_options(**self.execution_options(tenant_id))
        )
        if not result.rowcount:
            raise CompanyNotFoundError("Company not found.")

    async def delete(self, tenant_id, company_id):
        """Физически удаляет компанию текущего tenant."""
        result = await self.session.execute(
            delete(CompanyModel.__table__)
            .where(CompanyModel.__table__.c.id == company_id.uuid)
            .execution_options(**self.execution_options(tenant_id))
        )
        if not result.rowcount:
            raise CompanyNotFoundError("Company not found.")

    async def list(self, query: ListCompaniesQuery) -> CompanyPageDTO:
        """Ищет компании и возвращает offset-страницу со stable sort."""
        table = CompanyModel.__table__
        q = query.q.strip()
        clause = table.c.name.ilike(f"%{q}%") if q else None
        options = self.execution_options(query.tenant_id)
        count_statement = select(func.count()).select_from(table)
        list_statement = select(table)
        if clause is not None:
            count_statement = count_statement.where(clause)
            list_statement = list_statement.where(clause)
        total = int(
            await self.session.scalar(count_statement.execution_options(**options)) or 0
        )
        result = await self.session.execute(
            list_statement.order_by(func.lower(table.c.name), table.c.id)
            .offset(query.offset)
            .limit(query.limit)
            .execution_options(**options)
        )
        return CompanyPageDTO(
            items=tuple(company_dto(company_entity(row)) for row in result.mappings()),
            total=total,
            limit=query.limit,
            offset=query.offset,
        )


__all__ = ["SqlAlchemyCompanyRepository", "company_entity", "company_values"]
