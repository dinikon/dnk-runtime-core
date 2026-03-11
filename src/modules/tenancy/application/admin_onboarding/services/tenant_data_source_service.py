from __future__ import annotations

from typing import Protocol
from uuid import UUID

from src.modules.tenancy.application.admin_onboarding.ports.repositories import (
    TenantDataSourceRepositoryProtocol,
)
from src.modules.tenancy.domain.entities import TenantDataSource
from src.modules.tenancy.domain.errors import (
    TenantDataSourceAlreadyExistsError,
    TenantDataSourceSchemaAlreadyExistsError,
)


class TenantDataSourceServiceProtocol(Protocol):
    async def create_primary_local_data_source(
        self,
        *,
        tenant_id: UUID,
        schema: str,
    ) -> TenantDataSource: ...


class TenantDataSourceService:
    def __init__(
        self,
        tenant_data_sources_repository: TenantDataSourceRepositoryProtocol,
    ):
        self._tenant_data_sources_repository = tenant_data_sources_repository

    async def create_primary_local_data_source(
        self,
        tenant_id: UUID,
        schema: str,
    ) -> TenantDataSource:
        normalized_schema = schema.strip()
        if await self._tenant_data_sources_repository.get_by_tenant_id(tenant_id):
            raise TenantDataSourceAlreadyExistsError(tenant_id)
        if await self._tenant_data_sources_repository.exists_by_schema(
            normalized_schema
        ):
            raise TenantDataSourceSchemaAlreadyExistsError(normalized_schema)

        data_source = TenantDataSource.create_primary_local_data_source(
            tenant_id=tenant_id,
            schema=normalized_schema,
            dsn=None,
            is_remote=False,
            source_type="postgresql",
        )
        await self._tenant_data_sources_repository.add(data_source)
        return data_source
