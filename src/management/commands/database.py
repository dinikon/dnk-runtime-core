"""Public database installation without automatic adoption or resets."""

import argparse

from src.modules.shared.infrastructure.persistence.database_helper import db_helper
from src.modules.shared.infrastructure.persistence.global_migrations import (
    GlobalMigrator,
)
from src.modules.shared.infrastructure.persistence.tenant_migrations import (
    TenantMigrator,
)
from src.modules.shared.application.persistence.tenant_schema_naming import (
    TenantSchemaNaming,
)
from src.modules.tenancy.domain.tenant.value_object import TenantIdVO
from src.modules.tenancy.infrastructure.persistence.tenant import TenantModel
from src.config import dnk_config
from sqlalchemy import select


async def handle(args: argparse.Namespace) -> int:
    migrator = GlobalMigrator()
    try:
        async with db_helper.engine.begin() as connection:
            if args.database_action == "upgrade":
                await migrator.upgrade(connection)
                naming = TenantSchemaNaming(dnk_config.SCHEMA_PREFIX)
                tenant_migrator = TenantMigrator()
                for tenant_id in await connection.scalars(
                    select(TenantModel.id).order_by(TenantModel.id)
                ):
                    await tenant_migrator.upgrade(
                        connection, naming.schema_name(TenantIdVO.from_value(tenant_id))
                    )
            await migrator.require_current(connection)
        print(f"Runtime public schema is current: {migrator.head()}")
        return 0
    except Exception as exc:
        # Do not emit driver parameters, URLs or credentials.
        print(f"Runtime database command failed ({type(exc).__name__})")
        return 1
    finally:
        await db_helper.dispose()


def register(subparsers):
    parser = subparsers.add_parser(
        "database", help="Install/check the versioned public schema"
    )
    parser.add_argument("database_action", choices=("upgrade", "check"))
    parser.set_defaults(handler=handle)
