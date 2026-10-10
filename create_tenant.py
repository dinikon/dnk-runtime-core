import asyncio
import sys
from dataclasses import asdict

sys.path.insert(0, "src")

from src.modules.shared.infrastructure.persistence.database_helper import db_helper
from modules.shared.infrastructure.persistence.unit_of_work.sqlalchemy import UnitOfWork
from src.modules.tenancy.application.tenant.command.create_tenant_command import (
    CreateTenantCommand,
)
from src.modules.tenancy.presentation.depends import application as app
from src.modules.tenancy.presentation.depends import infrastructure as infra
from src.config import dnk_config
from src.modules.tenancy.application.tenant.tenant_schema_naming import (
    TenantSchemaNaming,
)
from src.modules.tenancy.presentation.depends.storage_management import (
    prepare_tenant_storage,
)


async def main() -> None:
    """Создаёт local tenant и активирует после подготовки приватного хранилища."""
    try:
        async with UnitOfWork(db_helper.session_factory) as uow:
            use_case = app.get_create_tenant_use_case(
                infra.get_tenant_onboarding_service(
                    infra.get_tenants_repository(uow),
                    infra.get_tenant_domains_repository(uow),
                ),
                infra.get_identity_provisioning_service(uow),
                app.get_tenant_schema_bootstrap_context_factory(),
                app.get_tenant_schema_bootstrap_port(uow),
                app.get_tenant_storage(uow),
            )
            result = await use_case.execute(
                CreateTenantCommand(
                    tenant_name="Local test",
                    external_id="local-test-denis",
                    tenant_domain_host="localhost",
                    user_first_name="Denis",
                    user_last_name="",
                    user_email="denis.inikon@gmail.com",
                )
            )
        await prepare_tenant_storage(
            db_helper.session_factory,
            TenantSchemaNaming(dnk_config.SCHEMA_PREFIX),
            result.tenant_id,
            activate=True,
        )
        print({**asdict(result), "tenant_status": "active"})
    finally:
        await db_helper.dispose()


asyncio.run(main())
