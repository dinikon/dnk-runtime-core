import unittest
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from src.modules.shared import EntityIdVO
from src.modules.tenancy.application.ports.schema_bootstrap import (
    TenantSchemaBootstrapContextFactory,
)
from src.modules.tenancy.domain.tenant.schema_error import (
    TenantSchemaAlreadyExistsError,
)
from src.modules.tenancy.infrastructure.adapter.schema_bootstrap import (
    AlembicTenantSchemaBootstrapAdapter,
)


class TenantSchemaBootstrapBoundaryTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.tenant_id = EntityIdVO.from_value(uuid4())
        self.context = TenantSchemaBootstrapContextFactory(schema_prefix="dnk_").build(
            tenant_id=self.tenant_id
        )

    def test_context_has_only_tenant_and_deterministic_schema(self):
        self.assertEqual(self.context.tenant_id, self.tenant_id.uuid)
        self.assertEqual(self.context.schema_name, f"dnk_{self.tenant_id.uuid.hex}")
        self.assertFalse(hasattr(self.context, "seed_path"))

    async def test_adapter_uses_current_session_and_never_commits(self):
        connection = AsyncMock()
        session = AsyncMock()
        session.connection.return_value = connection
        migrator = AsyncMock()
        adapter = AlembicTenantSchemaBootstrapAdapter(session, migrator)
        module = "src.modules.tenancy.infrastructure.adapter.schema_bootstrap"
        with (
            patch(f"{module}.lock_tenant_schema", new_callable=AsyncMock),
            patch(
                f"{module}.schema_exists", new_callable=AsyncMock, return_value=False
            ),
        ):
            await adapter.bootstrap(context=self.context)
        connection.execute.assert_awaited_once()
        migrator.upgrade.assert_awaited_once_with(connection, self.context.schema_name)
        session.commit.assert_not_awaited()
        connection.commit.assert_not_awaited()

    async def test_existing_schema_is_a_tenancy_conflict(self):
        session = AsyncMock()
        migrator = AsyncMock()
        module = "src.modules.tenancy.infrastructure.adapter.schema_bootstrap"
        with (
            patch(f"{module}.lock_tenant_schema", new_callable=AsyncMock),
            patch(f"{module}.schema_exists", new_callable=AsyncMock, return_value=True),
        ):
            with self.assertRaises(TenantSchemaAlreadyExistsError):
                await AlembicTenantSchemaBootstrapAdapter(session, migrator).bootstrap(
                    context=self.context
                )
        migrator.upgrade.assert_not_awaited()
