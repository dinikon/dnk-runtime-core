"""Composition adapter to tenancy and identity; no foreign ORM in application."""

from uuid import UUID

from sqlalchemy import or_, select, update

from src.modules.shared import EntityIdVO
from src.modules.shared.application.persistence.tenant_schema_naming import (
    TenantSchemaNaming,
)
from src.modules.shared.infrastructure.persistence.tenant_migrations import (
    TenantMigrator,
    schema_exists,
)
from src.modules.tenancy.application.ports.schema_bootstrap import (
    TenantSchemaBootstrapContextFactory,
)
from src.modules.tenancy.application.tenant.command import CreateTenantCommand
from src.modules.tenancy.application.tenant.use_case.create_tenant import (
    CreateTenantUseCase,
)
from src.modules.tenancy.domain.service import TenantOnboardingService
from src.modules.tenancy.infrastructure.adapter.identity_provisioning import (
    IdentityProvisioningServiceAdapter,
)
from src.modules.tenancy.infrastructure.adapter.schema_bootstrap import (
    AlembicTenantSchemaBootstrapAdapter,
)
from src.modules.tenancy.infrastructure.persistence.tenant import TenantModel
from src.modules.tenancy.infrastructure.persistence.tenant_domain import (
    TenantDomainModel,
)
from src.modules.tenancy.infrastructure.repository import (
    SqlAlchemyTenantDomainRepository,
    SqlAlchemyTenantRepository,
)


class TenancyAdapter:
    def __init__(self, session, schema_prefix: str):
        self.session = session
        self.naming = TenantSchemaNaming(schema_prefix)
        self.schema_prefix = schema_prefix
        self.migrator = TenantMigrator()

    async def inspect(self, tenant_id: UUID, hostname: str, external_id: str) -> str:
        """Absence requires all known physical identities to be absent."""
        tenant = await self.session.scalar(
            select(TenantModel.id)
            .where(
                or_(TenantModel.id == tenant_id, TenantModel.external_id == external_id)
            )
            .limit(1)
        )
        host = await self.session.scalar(
            select(TenantDomainModel.id)
            .where(
                or_(
                    TenantDomainModel.host == hostname,
                    TenantDomainModel.tenant_id == tenant_id,
                )
            )
            .limit(1)
        )
        connection = await self.session.connection()
        physical = await schema_exists(
            connection, self.naming.schema_name(EntityIdVO.from_value(tenant_id))
        )
        return (
            "present"
            if physical or tenant is not None or host is not None
            else "absent"
        )

    async def install(self, installation, command: dict):
        from src.modules.identity.application.user import UserService
        from src.modules.identity.infrastructure.repository import (
            SqlAlchemyUserRepository,
        )
        from src.modules.identity.infrastructure.cloud_owner import bind_cloud_owner

        use_case = CreateTenantUseCase(
            TenantOnboardingService(
                SqlAlchemyTenantRepository(self.session),
                SqlAlchemyTenantDomainRepository(self.session),
            ),
            IdentityProvisioningServiceAdapter(
                UserService(SqlAlchemyUserRepository(self.session, self.naming))
            ),
            TenantSchemaBootstrapContextFactory(schema_prefix=self.schema_prefix),
            AlembicTenantSchemaBootstrapAdapter(self.session, self.migrator),
        )
        profile = command["owner"].get("profile", {})
        result = await use_case.execute(
            CreateTenantCommand(
                tenant_name=command["name"],
                external_id=str(installation.core_tenant_id),
                tenant_domain_host=installation.hostname,
                user_first_name=profile.get("first_name", ""),
                user_last_name=profile.get("last_name", ""),
                user_email=command["owner"]["verified_email"],
                reserved_tenant_id=installation.runtime_tenant_id,
            )
        )
        await bind_cloud_owner(
            self.session,
            tenant_id=installation.runtime_tenant_id,
            user_id=result.user_id,
            issuer=command["oidc"]["issuer"],
            subject=command["owner"]["sub"],
            schema_prefix=self.schema_prefix,
        )
        installation.owner_user_id = result.user_id

    async def ready(
        self, installation, command: dict, *, require_active: bool = False
    ) -> bool:
        from src.modules.identity.infrastructure.cloud_owner import cloud_owner_ready

        tenant = await self.session.get(TenantModel, installation.runtime_tenant_id)
        if tenant is None or (require_active and tenant.status != "active"):
            return False
        domain = await self.session.scalar(
            select(TenantDomainModel).where(
                TenantDomainModel.host == installation.hostname
            )
        )
        if domain is None or domain.tenant_id != tenant.id or domain.status != "active":
            return False
        connection = await self.session.connection()
        schema = self.naming.schema_name(EntityIdVO.from_value(tenant.id))
        if not await schema_exists(connection, schema):
            return False
        if await self.migrator.current(connection, schema) != (self.migrator.head(),):
            return False
        if require_active:
            # A completed installation stays ready when its original owner is
            # later suspended or explicitly unlinks their cloud account.
            return True
        if installation.owner_user_id is None:
            return False
        return await cloud_owner_ready(
            self.session,
            tenant_id=tenant.id,
            user_id=installation.owner_user_id,
            issuer=command["oidc"]["issuer"],
            subject=command["owner"]["sub"],
            schema_prefix=self.schema_prefix,
        )

    async def activate(self, tenant_id: UUID) -> None:
        await self.session.execute(
            update(TenantModel)
            .where(TenantModel.id == tenant_id)
            .values(status="active")
        )
