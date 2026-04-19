from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.tenancy.domain.tenant_domain import (
    TenantDomain,
    TenantDomainRepositoryProtocol,
    TenantDomainStatus,
    TenantServiceType,
)
from src.modules.tenancy.infrastructure.mapper import (
    tenant_domain_model_to_entity,
    tenant_domain_to_model,
)
from src.modules.tenancy.infrastructure.persistence.tenant_domain import (
    TenantDomainModel,
)


class SqlAlchemyTenantDomainRepository(TenantDomainRepositoryProtocol):
    """SQLAlchemy-репозиторий tenant domain entities."""

    def __init__(self, session: AsyncSession) -> None:
        """Инициализирует repository текущей async-сессией."""
        self._session = session

    async def add(self, domain: TenantDomain) -> None:
        """Добавляет tenant domain model и flush-ит сессию."""
        self._session.add(tenant_domain_to_model(domain))
        await self._session.flush()

    async def get_by_id(self, domain_id: UUID) -> TenantDomain | None:
        """Ищет tenant domain по id."""
        model: TenantDomainModel | None = (
            await self._session.scalars(
                select(TenantDomainModel).where(TenantDomainModel.id == domain_id)
            )
        ).one_or_none()

        if model is None:
            return None
        return tenant_domain_model_to_entity(model)

    async def get_by_host(self, host: str) -> TenantDomain | None:
        """Ищет не удаленный tenant domain по host."""
        model: TenantDomainModel | None = (
            await self._session.scalars(
                select(TenantDomainModel)
                .where(TenantDomainModel.host == host)
                .where(TenantDomainModel.status != TenantDomainStatus.DELETED)
            )
        ).one_or_none()

        if model is None:
            return None
        return tenant_domain_model_to_entity(model)

    async def get_api_host_by_tenant_id(self, tenant_id: UUID) -> str | None:
        """Возвращает preferred API host tenant, если он зарегистрирован."""
        host: str | None = (
            await self._session.scalars(
                select(TenantDomainModel.host)
                .where(TenantDomainModel.tenant_id == tenant_id)
                .where(TenantDomainModel.service_type == TenantServiceType.API)
                .where(TenantDomainModel.status != TenantDomainStatus.DELETED)
                .order_by(
                    TenantDomainModel.is_primary.desc(),
                    TenantDomainModel.created_at,
                )
                .limit(1)
            )
        ).one_or_none()

        return host

    async def exists_by_host(self, host: str) -> bool:
        """Проверяет существование не удаленного tenant domain по host."""
        domain_id: UUID | None = (
            await self._session.scalars(
                select(TenantDomainModel.id)
                .where(TenantDomainModel.host == host)
                .where(TenantDomainModel.status != TenantDomainStatus.DELETED)
                .limit(1)
            )
        ).one_or_none()

        return domain_id is not None


__all__ = ["SqlAlchemyTenantDomainRepository"]
