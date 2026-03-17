from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.tenancy.domain.entities import Tenant, TenantDomain
from src.modules.tenancy.domain.repositories import (
    TenantDomainRepositoryProtocol,
    TenantRepositoryProtocol,
)
from src.modules.tenancy.domain.value_objects import (
    TenantDomainStatus,
    TenantServiceType,
)
from src.modules.tenancy.infrastructure.mappers import (
    tenant_domain_model_to_entity,
    tenant_domain_to_model,
    tenant_model_to_entity,
    tenant_to_model,
)
from src.modules.tenancy.infrastructure.persistence.tenant import TenantModel
from src.modules.tenancy.infrastructure.persistence.tenant_domain import (
    TenantDomainModel,
)


class SqlAlchemyTenantRepository(TenantRepositoryProtocol):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def add(self, tenant: Tenant) -> None:
        self._session.add(tenant_to_model(tenant))
        await self._session.flush()

    async def get_by_id(self, tenant_id: UUID) -> Tenant | None:
        model = await self._session.scalar(
            select(TenantModel).where(TenantModel.id == str(tenant_id))
        )
        if model is None:
            return None
        return tenant_model_to_entity(model)

    async def get_by_name(self, name: str) -> Tenant | None:
        model = await self._session.scalar(
            select(TenantModel).where(TenantModel.name == name)
        )
        if model is None:
            return None
        return tenant_model_to_entity(model)

    async def exists_by_external_id(self, external_id: str) -> bool:
        tenant_id = await self._session.scalar(
            select(TenantModel.id)
            .where(TenantModel.external_id == external_id)
            .limit(1)
        )
        return tenant_id is not None

    async def exists_by_name(self, name: str) -> bool:
        tenant_id = await self._session.scalar(
            select(TenantModel.id).where(TenantModel.name == name).limit(1)
        )
        return tenant_id is not None


class SqlAlchemyTenantDomainRepository(TenantDomainRepositoryProtocol):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def add(self, domain: TenantDomain) -> None:
        self._session.add(tenant_domain_to_model(domain))
        await self._session.flush()

    async def get_by_id(self, domain_id: UUID) -> TenantDomain | None:
        model = await self._session.scalar(
            select(TenantDomainModel).where(TenantDomainModel.id == str(domain_id))
        )
        if model is None:
            return None
        return tenant_domain_model_to_entity(model)

    async def get_by_host(self, host: str) -> TenantDomain | None:
        model = await self._session.scalar(
            select(TenantDomainModel)
            .where(TenantDomainModel.host == host)
            .where(TenantDomainModel.status != TenantDomainStatus.DELETED)
        )
        if model is None:
            return None
        return tenant_domain_model_to_entity(model)

    async def get_api_host_by_tenant_id(self, tenant_id: UUID) -> str | None:
        return await self._session.scalar(
            select(TenantDomainModel.host)
            .where(TenantDomainModel.tenant_id == str(tenant_id))
            .where(TenantDomainModel.service_type == TenantServiceType.API)
            .where(TenantDomainModel.status != TenantDomainStatus.DELETED)
            .order_by(TenantDomainModel.is_primary.desc(), TenantDomainModel.created_at)
            .limit(1)
        )

    async def exists_by_host(self, host: str) -> bool:
        domain_id = await self._session.scalar(
            select(TenantDomainModel.id)
            .where(TenantDomainModel.host == host)
            .where(TenantDomainModel.status != TenantDomainStatus.DELETED)
            .limit(1)
        )
        return domain_id is not None
