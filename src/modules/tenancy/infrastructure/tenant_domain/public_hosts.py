from uuid import UUID
from sqlalchemy import select, case
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.tenancy.infrastructure.persistence.tenant_domain import (
    TenantDomainModel as D,
)


class SqlAlchemyTenantPublicHosts:
    """Реализует публичный фасад доменов проекциями Tenancy без восстановления roots."""

    def __init__(self, session: AsyncSession) -> None:
        """Получает общую сессию внешнего UoW без управления транзакцией."""
        self.session = session

    async def primary_host(self, tenant_id: UUID) -> str | None:
        """Предпочитает основной Console host; отключённые домены не публикуются."""
        return await self.session.scalar(
            select(D.host)
            .where(
                D.tenant_id == tenant_id,
                D.status == "active",
                D.verification_status == "verified",
                D.is_wildcard.is_(False),
                D.service_type.in_(("console", "http")),
            )
            .order_by(
                case((D.service_type == "console", 0), else_=1),
                D.is_primary.desc(),
                D.created_at,
                D.id,
            )
            .limit(1)
        )

    async def owns_host(self, tenant_id: UUID, host: str) -> bool:
        """Проверяет активный зарегистрированный домен, включая его tenant."""
        return (
            await self.session.scalar(
                select(D.id)
                .where(
                    D.tenant_id == tenant_id,
                    D.host == host,
                    D.status == "active",
                    D.verification_status == "verified",
                    D.is_wildcard.is_(False),
                    D.service_type.in_(("console", "http")),
                )
                .limit(1)
            )
            is not None
        )

    async def api_host(self, tenant_id: UUID) -> str | None:
        """Не публикует непроверенный, отключённый или wildcard API host."""
        host = await self.session.scalar(
            select(D.host)
            .where(
                D.tenant_id == tenant_id,
                D.status == "active",
                D.verification_status == "verified",
                D.is_wildcard.is_(False),
                D.service_type == "http",
            )
            .order_by(D.is_primary.desc(), D.created_at, D.id)
            .limit(1)
        )
        return host if host is not None else await self.primary_host(tenant_id)
