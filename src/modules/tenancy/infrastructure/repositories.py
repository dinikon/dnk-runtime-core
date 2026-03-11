from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.tenancy.domain.value_objects.tenant_domain_kind import (
    TenantDomainKind,
)
from src.modules.tenancy.domain.value_objects.tenant_domain_tls_mode import (
    TenantDomainTlsMode,
)
from src.modules.tenancy.domain.value_objects.tenant_domain_verification_status import (
    TenantDomainVerificationStatus,
)
from src.modules.tenancy.domain.value_objects.tenant_domain_status import (
    TenantDomainStatus,
)
from src.modules.tenancy.domain.value_objects.tenant_service_type import (
    TenantServiceType,
)
from src.modules.tenancy.domain.value_objects.tenant_status import TenantStatus
from src.modules.tenancy.application.admin_onboarding.ports.repositories import (
    TenantDataSourceRepositoryProtocol,
    TenantDomainRepositoryProtocol,
    TenantRepositoryProtocol,
)
from src.modules.tenancy.domain.entities import Tenant, TenantDataSource, TenantDomain
from src.modules.tenancy.infrastructure.persistence.data_source import (
    TenantDataSourceModel,
)
from src.modules.tenancy.infrastructure.persistence.tenant import TenantModel
from src.modules.tenancy.infrastructure.persistence.tenant_domain import (
    TenantDomainModel,
)


class SqlAlchemyTenantRepository(TenantRepositoryProtocol):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def add(self, tenant: Tenant) -> None:
        self._session.add(
            TenantModel(
                id=tenant.id,
                name=tenant.name,
                external_id=tenant.external_id,
                status=tenant.status,
                custom_config=tenant.custom_config,
                created_at=tenant.created_at,
                updated_at=tenant.updated_at,
            )
        )
        await self._session.flush()

    async def get_by_id(self, tenant_id: UUID) -> Tenant | None:
        model = await self._session.scalar(
            select(TenantModel).where(TenantModel.id == str(tenant_id))
        )
        if model is None:
            return None
        return self._map_tenant(model)

    async def get_by_name(self, name: str) -> Tenant | None:
        model = await self._session.scalar(
            select(TenantModel).where(TenantModel.name == name)
        )
        if model is None:
            return None
        return self._map_tenant(model)

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

    @staticmethod
    def _map_tenant(model: TenantModel) -> Tenant:
        return Tenant(
            id=_to_uuid(model.id),
            name=model.name,
            external_id=model.external_id,
            status=TenantStatus(model.status),
            custom_config=model.custom_config,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )


class SqlAlchemyTenantDomainRepository(TenantDomainRepositoryProtocol):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def add(self, domain: TenantDomain) -> None:
        self._session.add(
            TenantDomainModel(
                id=domain.id,
                tenant_id=str(domain.tenant_id),
                service_type=domain.service_type,
                kind=domain.kind,
                host=domain.host,
                base_path=domain.base_path,
                auth_mode=domain.auth_mode,
                status=domain.status,
                is_primary=domain.is_primary,
                is_wildcard=domain.is_wildcard,
                parent_domain=domain.parent_domain,
                verification_status=domain.verification_status,
                tls_mode=domain.tls_mode,
                metadata_json=domain.metadata_json,
                created_at=domain.created_at,
                updated_at=domain.updated_at,
            )
        )
        await self._session.flush()

    async def get_by_id(self, domain_id: UUID) -> TenantDomain | None:
        model = await self._session.scalar(
            select(TenantDomainModel).where(TenantDomainModel.id == str(domain_id))
        )
        if model is None:
            return None
        return self._map_domain(model)

    async def get_by_host(self, host: str) -> TenantDomain | None:
        model = await self._session.scalar(
            select(TenantDomainModel)
            .where(TenantDomainModel.host == host)
            .where(TenantDomainModel.status != TenantDomainStatus.DELETED)
        )
        if model is None:
            return None
        return self._map_domain(model)

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

    @staticmethod
    def _map_domain(model: TenantDomainModel) -> TenantDomain:
        return TenantDomain(
            id=_to_uuid(model.id),
            tenant_id=_to_uuid(model.tenant_id),
            service_type=TenantServiceType(model.service_type),
            kind=TenantDomainKind(model.kind),
            host=model.host,
            base_path=model.base_path,
            auth_mode=model.auth_mode,
            status=TenantDomainStatus(model.status),
            is_primary=model.is_primary,
            is_wildcard=model.is_wildcard,
            parent_domain=model.parent_domain,
            verification_status=TenantDomainVerificationStatus(
                model.verification_status
            ),
            tls_mode=TenantDomainTlsMode(model.tls_mode),
            metadata_json=model.metadata_json,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )


class SqlAlchemyTenantDataSourceRepository(TenantDataSourceRepositoryProtocol):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def add(self, data_source: TenantDataSource) -> None:
        self._session.add(
            TenantDataSourceModel(
                id=data_source.id,
                tenant_id=str(data_source.tenant_id),
                type=data_source.type,
                is_remote=data_source.is_remote,
                dsn=data_source.dsn,
                schema=data_source.schema,
                created_at=data_source.created_at,
                updated_at=data_source.updated_at,
            )
        )
        await self._session.flush()

    async def get_by_tenant_id(self, tenant_id: UUID) -> TenantDataSource | None:
        model = await self._session.scalar(
            select(TenantDataSourceModel).where(
                TenantDataSourceModel.tenant_id == str(tenant_id)
            )
        )
        if model is None:
            return None
        return self._map_data_source(model)

    async def exists_by_schema(self, schema: str) -> bool:
        data_source_id = await self._session.scalar(
            select(TenantDataSourceModel.id)
            .where(TenantDataSourceModel.schema == schema)
            .limit(1)
        )
        return data_source_id is not None

    @staticmethod
    def _map_data_source(model: TenantDataSourceModel) -> TenantDataSource:
        return TenantDataSource(
            id=_to_uuid(model.id),
            tenant_id=_to_uuid(model.tenant_id),
            type=model.type,
            is_remote=model.is_remote,
            dsn=model.dsn,
            schema=model.schema,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )


def _to_uuid(value: UUID | str) -> UUID:
    if isinstance(value, UUID):
        return value
    return UUID(value)
