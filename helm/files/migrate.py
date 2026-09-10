"""Bootstrap shared tables and migrate every tenant in one PostgreSQL transaction.

The mounted runner uses APIs already shipped in the published runtime image.
It never resets schemas or retries work after obtaining its connection/lock.
Existing shared tables are not altered: their versioned evolution is outside
this chart's current contract.
"""

import argparse
import asyncio
import hashlib
import sys
import time
from pathlib import Path

LOCK_KEY = int.from_bytes(
    hashlib.sha256(b"dnk:runtime:deployment").digest()[:8], signed=True
)


async def prepare(engine, bootstrap, tenant_ids, upgrade_tenant, wait_timeout=300):
    """Callbacks receive the exact connection that owns the transaction lock."""
    from sqlalchemy import text
    from sqlalchemy.exc import DBAPIError

    deadline = time.monotonic() + wait_timeout
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError("PostgreSQL readiness timeout")
        try:
            connection = await asyncio.wait_for(engine.connect(), timeout=remaining)
            break
        except (DBAPIError, OSError, TimeoutError):
            if time.monotonic() >= deadline:
                raise TimeoutError("PostgreSQL readiness timeout") from None
            await asyncio.sleep(min(1, max(0, deadline - time.monotonic())))

    try:
        async with connection.begin():
            # This transaction has one physical connection until commit/rollback.
            while not await connection.scalar(
                text("SELECT pg_try_advisory_xact_lock(:key)"), {"key": LOCK_KEY}
            ):
                if time.monotonic() >= deadline:
                    raise TimeoutError("Runtime migration lock timeout")
                await asyncio.sleep(min(0.2, max(0, deadline - time.monotonic())))
            await connection.execute(text("SET LOCAL search_path TO public"))
            # Bound waits on tenant locks acquired by the existing migrator too.
            remaining_ms = max(1, int((deadline - time.monotonic()) * 1000))
            await connection.execute(
                text("SELECT set_config('lock_timeout', :timeout, true)"),
                {"timeout": f"{remaining_ms}ms"},
            )
            await bootstrap(connection)
            for tenant_id in await tenant_ids(connection):
                await upgrade_tenant(connection, tenant_id)
    finally:
        await connection.close()


async def run(wait_timeout):
    # The image's CLI supports both src.* and modules.* imports this same way.
    root = Path.cwd()
    sys.path[:0] = [str(root), str(root / "src")]
    from sqlalchemy import select
    from src.config import dnk_config
    from src.modules.shared.infrastructure.persistence.base import Base
    from src.modules.shared.infrastructure.persistence.database_helper import db_helper
    from src.modules.shared.infrastructure.persistence.tenant_migrations import (
        TenantMigrator,
    )
    from src.modules.shared.application.persistence.tenant_schema_naming import (
        TenantSchemaNaming,
    )
    from src.modules.tenancy.domain.tenant.value_object import TenantIdVO
    from src.modules.tenancy.infrastructure.persistence.tenant import TenantModel

    migrator = TenantMigrator()
    naming = TenantSchemaNaming(dnk_config.SCHEMA_PREFIX)

    async def bootstrap(connection):
        await connection.run_sync(Base.metadata.create_all)

    async def tenant_ids(connection):
        result = await connection.scalars(
            select(TenantModel.id).order_by(TenantModel.id)
        )
        return list(result)

    async def upgrade(connection, tenant_id):
        await migrator.upgrade(
            connection, naming.schema_name(TenantIdVO.from_value(tenant_id))
        )

    try:
        await prepare(db_helper.engine, bootstrap, tenant_ids, upgrade, wait_timeout)
    finally:
        await db_helper.engine.dispose()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wait-timeout", type=float, default=300)
    args = parser.parse_args()
    if args.wait_timeout <= 0:
        parser.error("--wait-timeout must be positive")
    try:
        asyncio.run(run(args.wait_timeout))
    except Exception as error:
        # Driver errors may contain connection credentials or bound parameters.
        print(
            f"Runtime migrations failed ({type(error).__name__}); batch rolled back",
            file=sys.stderr,
        )
        return 1
    print("Runtime migrations completed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
