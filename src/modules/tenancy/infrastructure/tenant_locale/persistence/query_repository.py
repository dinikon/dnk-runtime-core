from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.tenancy.application.tenant_locale.port.query_repository import (
    TenantLocaleRecord,
)
from src.modules.tenancy.domain.tenant_locale.value_object.code import (
    TenantLocaleCodeVO,
)
from src.modules.tenancy.infrastructure.tenant_locale.persistence.model import (
    TenantLocaleModel,
)


class SqlAlchemyTenantLocaleQueryRepository:
    """Читает проекции из общей сессии без выбора схемы в запросе."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_all(self) -> list[TenantLocaleRecord]:
        rows = (
            await self._session.execute(
                select(
                    TenantLocaleModel.code,
                    TenantLocaleModel.created_at,
                    TenantLocaleModel.created_by,
                ).order_by(TenantLocaleModel.code)
            )
        ).all()
        return [
            TenantLocaleRecord(code, created_at, created_by)
            for code, created_at, created_by in rows
        ]

    async def contains(self, code: TenantLocaleCodeVO) -> bool:
        found = await self._session.scalar(
            select(TenantLocaleModel.code)
            .where(TenantLocaleModel.code == code.value)
            .limit(1)
        )
        return found is not None
