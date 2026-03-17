from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import src.modules.persistence  # noqa: F401
from src.modules.runtime_schema.infrastructure.repositories import (
    SqlAlchemyDataSourceRepository,
    SqlAlchemyObjectMetadataRepository,
)
from src.modules.shared.db.base import Base
from src.modules.shared.db.uow import UnitOfWork
from src.modules.tenancy.application.commands import CreateTenantCommand
from src.modules.tenancy.application.ports.identity import ProvisionedTenantAdmin
from src.modules.tenancy.application.use_cases.create_tenant import CreateTenantUseCase
from src.modules.tenancy.infrastructure.repositories import (
    SqlAlchemyTenantDomainRepository,
    SqlAlchemyTenantRepository,
)
from src.modules.tenancy.infrastructure.runtime_schema_bootstrapper import (
    SqlAlchemyRuntimeSchemaBootstrapper,
)


class _FakeIdentityProvisioningService:
    async def create_tenant_admin(
        self,
        tenant_id: UUID,
        first_name: str,
        last_name: str,
        email: str,
    ) -> ProvisionedTenantAdmin:
        return ProvisionedTenantAdmin(
            user_id=uuid4(),
            user_email_id=uuid4(),
            user_status="active",
        )


class TestTenantBootstrapStep11(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self._temp_dir = tempfile.TemporaryDirectory()
        database_path = Path(self._temp_dir.name) / "step11_tenant_bootstrap.sqlite3"

        self._engine = create_async_engine(
            f"sqlite+aiosqlite:///{database_path}",
            future=True,
        )
        self._session_factory = async_sessionmaker(
            bind=self._engine,
            expire_on_commit=False,
        )

        async with self._engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    async def asyncTearDown(self) -> None:
        await self._engine.dispose()
        self._temp_dir.cleanup()

    async def test_create_tenant_runs_full_bootstrap_flow(self) -> None:
        uow = UnitOfWork(self._session_factory)
        async with uow:
            use_case = self._build_create_tenant_use_case(uow=uow)
            result = await use_case.execute(
                CreateTenantCommand(
                    tenant_name="Acme",
                    external_id="acme-ext",
                    tenant_domain_host="acme.local",
                    user_last_name="Doe",
                    user_first_name="Jane",
                    user_email="jane@example.com",
                )
            )

        async with self._session_factory() as session:
            data_sources_count = await _count_rows(
                session=session,
                sql=(
                    "SELECT COUNT(*) FROM runtime_data_source_metadata "
                    "WHERE tenant_id = :tenant_id"
                ),
                params={"tenant_id": str(result.tenant_id)},
            )
            objects_count = await _count_rows(
                session=session,
                sql=(
                    "SELECT COUNT(*) FROM runtime_object_metadata "
                    "WHERE tenant_id = :tenant_id"
                ),
                params={"tenant_id": str(result.tenant_id)},
            )
            contacts_count = await _count_rows(
                session=session,
                sql='SELECT COUNT(*) FROM "contacts"',
                params={},
            )
            companies_count = await _count_rows(
                session=session,
                sql='SELECT COUNT(*) FROM "companies"',
                params={},
            )

            object_names = await _fetch_column_values(
                session=session,
                sql=(
                    "SELECT name_singular FROM runtime_object_metadata "
                    "WHERE tenant_id = :tenant_id ORDER BY name_singular"
                ),
                params={"tenant_id": str(result.tenant_id)},
            )
            source_types = await _fetch_column_values(
                session=session,
                sql=(
                    "SELECT type FROM runtime_data_source_metadata "
                    "WHERE tenant_id = :tenant_id"
                ),
                params={"tenant_id": str(result.tenant_id)},
            )

        self.assertEqual(data_sources_count, 1)
        self.assertEqual(objects_count, 2)
        self.assertEqual(set(object_names), {"company", "contact"})
        self.assertEqual(source_types, ["postgresql"])
        self.assertGreaterEqual(contacts_count, 1)
        self.assertGreaterEqual(companies_count, 1)

    async def test_bootstrapper_rerun_is_idempotent(self) -> None:
        uow = UnitOfWork(self._session_factory)
        async with uow:
            use_case = self._build_create_tenant_use_case(uow=uow)
            result = await use_case.execute(
                CreateTenantCommand(
                    tenant_name="Beta",
                    external_id="beta-ext",
                    tenant_domain_host="beta.local",
                    user_last_name="Doe",
                    user_first_name="John",
                    user_email="john@example.com",
                )
            )

        uow = UnitOfWork(self._session_factory)
        async with uow:
            bootstrapper = self._build_bootstrapper(uow=uow)
            await bootstrapper.bootstrap_tenant(result.tenant_id)
            await uow.commit()

        async with self._session_factory() as session:
            data_sources_count = await _count_rows(
                session=session,
                sql=(
                    "SELECT COUNT(*) FROM runtime_data_source_metadata "
                    "WHERE tenant_id = :tenant_id"
                ),
                params={"tenant_id": str(result.tenant_id)},
            )
            objects_count = await _count_rows(
                session=session,
                sql=(
                    "SELECT COUNT(*) FROM runtime_object_metadata "
                    "WHERE tenant_id = :tenant_id"
                ),
                params={"tenant_id": str(result.tenant_id)},
            )
            seeded_contacts_count = await _count_rows(
                session=session,
                sql='SELECT COUNT(*) FROM "contacts" WHERE last_name = :last_name',
                params={"last_name": "Seed"},
            )
            seeded_companies_count = await _count_rows(
                session=session,
                sql='SELECT COUNT(*) FROM "companies" WHERE last_name = :last_name',
                params={"last_name": "Seed"},
            )

        self.assertEqual(data_sources_count, 1)
        self.assertEqual(objects_count, 2)
        self.assertEqual(seeded_contacts_count, 1)
        self.assertEqual(seeded_companies_count, 1)

    def _build_create_tenant_use_case(self, *, uow: UnitOfWork) -> CreateTenantUseCase:
        return CreateTenantUseCase(
            uow=uow,
            tenants_repository=SqlAlchemyTenantRepository(uow.session),
            tenant_domains_repository=SqlAlchemyTenantDomainRepository(uow.session),
            identity_provisioning_service=_FakeIdentityProvisioningService(),
            runtime_schema_bootstrapper=self._build_bootstrapper(uow=uow),
        )

    def _build_bootstrapper(
        self,
        *,
        uow: UnitOfWork,
    ) -> SqlAlchemyRuntimeSchemaBootstrapper:
        session = uow.session
        assert session is not None
        return SqlAlchemyRuntimeSchemaBootstrapper(
            session=session,
            data_source_repository=SqlAlchemyDataSourceRepository(session),
            object_metadata_repository=SqlAlchemyObjectMetadataRepository(session),
        )


async def _count_rows(
    *,
    session: AsyncSession,
    sql: str,
    params: dict[str, object],
) -> int:
    rows = await session.execute(text(sql), params)
    return int(rows.scalar_one())


async def _fetch_column_values(
    *,
    session: AsyncSession,
    sql: str,
    params: dict[str, object],
) -> list[str]:
    rows = await session.execute(text(sql), params)
    return [str(row[0]) for row in rows.fetchall()]


if __name__ == "__main__":
    unittest.main()
