from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.tenancy.domain.tenant import Tenant, TenantRepositoryProtocol
from src.modules.tenancy.infrastructure.mapper import (
    tenant_model_to_entity,
    tenant_to_model,
)
from src.modules.tenancy.infrastructure.persistence.tenant import TenantModel


class SqlAlchemyTenantRepository(TenantRepositoryProtocol):
    """SQLAlchemy-репозиторий tenant entities."""

    def __init__(self, session: AsyncSession) -> None:
        """Инициализирует repository текущей async-сессией."""
        self._session = session

    async def add(self, tenant: Tenant) -> None:
        """Добавляет tenant model и flush-ит сессию."""
        self._session.add(tenant_to_model(tenant))
        await self._session.flush()

    async def get_by_id(self, tenant_id: UUID) -> Tenant | None:
        """Ищет tenant по id."""
        model = await self._session.scalar(
            select(TenantModel).where(TenantModel.id == str(tenant_id))
        )
        if model is None:
            return None
        return tenant_model_to_entity(model)

    async def get_by_name(self, name: str) -> Tenant | None:
        """Ищет tenant по имени."""
        model = await self._session.scalar(
            select(TenantModel).where(TenantModel.name == name)
        )
        if model is None:
            return None
        return tenant_model_to_entity(model)

    async def exists_by_external_id(self, external_id: str) -> bool:
        """Проверяет существование tenant по external_id."""
        tenant_id = await self._session.scalar(
            select(TenantModel.id)
            .where(TenantModel.external_id == external_id)
            .limit(1)
        )
        return tenant_id is not None

    async def exists_by_name(self, name: str) -> bool:
        """Проверяет существование tenant по имени."""
        tenant_id = await self._session.scalar(
            select(TenantModel.id).where(TenantModel.name == name).limit(1)
        )
        return tenant_id is not None


__all__ = ["SqlAlchemyTenantRepository"]
