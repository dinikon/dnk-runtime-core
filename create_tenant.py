import asyncio
import sys
from dataclasses import asdict

sys.path.insert(0, "src")

from src.modules.shared.infrastructure.persistence.database_helper import db_helper
from src.modules.shared.infrastructure.persistence.unit_of_work import UnitOfWork
from src.modules.tenancy.application.tenant.command import CreateTenantCommand
from src.modules.tenancy.presentation.depends import application as app
from src.modules.tenancy.presentation.depends import infrastructure as infra


async def main():
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
        print(asdict(result))
    finally:
        await db_helper.dispose()


asyncio.run(main())