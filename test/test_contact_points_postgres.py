"""Real HTTP/DI/PostgreSQL integration; requires an explicitly disposable database."""

from dataclasses import replace
import os
import unittest
from uuid import uuid4
from unittest.mock import patch

from fastapi import FastAPI, Request, Response
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool
from sqlalchemy.schema import CreateSchema, DropSchema

from src.config import dnk_config
from src.modules.contact_points.presentation.http.router import router as points_router
from src.modules.identity.presentation.http.csrf import issue_csrf
from src.modules.identity.presentation.auth.depends import (
    require_authenticated_request_context,
)
from src.modules.identity.domain.auth.principal import Principal
from src.modules.identity.domain.auth.request_context import RequestContext
from src.modules.shared.application.tokens import TokenManager
from src.modules.shared.infrastructure.tokens import InMemoryTokenBackend
from src.modules.shared.presentation.tokens.depends import TokenManagerDep
from src.modules.shared.application.persistence.tenant_schema_naming import (
    TenantSchemaNaming,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.shared.infrastructure.persistence.tenant_migrations import (
    TenantMigrator,
)
from src.modules.shared.infrastructure.persistence import UnitOfWork
from src.modules.contact_points.infrastructure.persistence import (
    ContactPointLabelModel,
)
from src.modules.contact_points.infrastructure.persistence.repository.binding_repository import (
    SqlAlchemyContactPointBindingRepository,
)
from src.modules.contact_points.infrastructure.persistence import (
    SqlAlchemyContactPointRepository,
)
from src.modules.contact_points.domain.contact_point.value_object.value import (
    ContactPointType,
)
from src.modules.crm.infrastructure.persistence.models.contact import ContactModel

TEST_URL = os.environ.get("TEST_POSTGRES_URL")


@unittest.skipUnless(
    TEST_URL, "Set TEST_POSTGRES_URL to a disposable PostgreSQL database."
)
class ContactPointsPostgresTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine(TEST_URL, poolclass=NullPool)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        self.naming = TenantSchemaNaming(dnk_config.SCHEMA_PREFIX)
        self.tenant = EntityIdVO.from_value(uuid4())
        self.other = EntityIdVO.from_value(uuid4())
        self.actor = uuid4()
        self.schemas = [
            self.naming.schema_name(tenant) for tenant in (self.tenant, self.other)
        ]
        async with self.engine.begin() as connection:
            for schema in self.schemas:
                await connection.execute(CreateSchema(schema))
                await TenantMigrator().upgrade(connection, schema)
        self.context = RequestContext(
            principal=Principal(
                user_id=str(self.actor),
                tenant_id=str(self.tenant),
                session_id="test",
                roles=("admin",),
            ),
            request_id=None,
            ip=None,
            user_agent=None,
        )
        self.app = FastAPI()
        self.app.state.db = self.sessions
        self.app.state.token_manager = TokenManager(InMemoryTokenBackend())
        self.app.include_router(points_router, prefix="/api/console")
        self.app.dependency_overrides[require_authenticated_request_context] = (
            lambda: self.context
        )

        @self.app.get("/csrf")
        async def csrf(request: Request, response: Response, tokens: TokenManagerDep):
            return await issue_csrf(request, response, tokens)

        self.client = AsyncClient(
            transport=ASGITransport(app=self.app), base_url="https://tenant.example"
        )
        response = await self.client.get("/csrf")
        self.headers = {
            "Origin": "https://tenant.example",
            "X-CSRF-Token": response.json()["csrf_token"],
        }

    async def asyncTearDown(self):
        await self.client.aclose()
        async with self.engine.begin() as connection:
            for schema in self.schemas:
                await connection.execute(
                    DropSchema(schema, cascade=True, if_exists=True)
                )
        await self.engine.dispose()

    async def request(self, method, path, **kwargs):
        return await self.client.request(
            method, "/api/console/" + path, headers=self.headers, **kwargs
        )

    async def count(self, model, tenant=None):
        async with self.sessions() as session:
            return await session.scalar(
                select(func.count())
                .select_from(model.__table__)
                .execution_options(
                    schema_translate_map={
                        "tenant": self.naming.schema_name(tenant or self.tenant)
                    }
                )
            )

    async def test_request_dependency_graph_shares_session_and_commits_once(self):
        from src.modules.contact_points.presentation.depends.infrastructure import (
            ContactPointRepositoryDep,
            ContactPointBindingRepositoryDep,
            ContactPointLabelRepositoryDep,
        )
        from src.modules.shared.presentation.persistence.depends import UoWDep

        @self.app.get("/di-probe")
        async def probe(
            uow: UoWDep,
            points: ContactPointRepositoryDep,
            bindings: ContactPointBindingRepositoryDep,
            labels: ContactPointLabelRepositoryDep,
        ):
            return {
                "same_session": all(
                    repository._session is uow.session
                    for repository in (points, bindings, labels)
                )
            }

        self.assertEqual(
            (await self.client.get("/di-probe")).json(), {"same_session": True}
        )
        commits = []
        original = UnitOfWork.commit

        async def track_commit(uow):
            commits.append(uow.session)
            await original(uow)

        with patch.object(UnitOfWork, "commit", track_commit):
            response = await self.request(
                "POST", "contact-points/labels", json={"type": "phone", "name": "New"}
            )
            self.assertEqual(response.status_code, 201, response.text)
        self.assertEqual(len(commits), 1)

    async def test_same_ids_in_two_tenants_through_one_session_and_repositories(self):
        from datetime import UTC, datetime, timedelta
        from src.modules.contact_points.domain.contact_point.entity import ContactPoint
        from src.modules.contact_points.domain.contact_point.value_object.identifier import (
            ContactPointIdVO,
        )
        from src.modules.contact_points.domain.contact_point.value_object.value import (
            NormalizationContext,
        )
        from src.modules.contact_points.domain.binding.entity import ContactPointBinding
        from src.modules.contact_points.domain.binding.value_object.identifier import (
            ContactPointBindingIdVO,
        )
        from src.modules.contact_points.domain.binding.value_object.target import (
            ContactPointTargetVO,
        )
        from src.modules.contact_points.domain.label.entity import ContactPointLabel
        from src.modules.contact_points.domain.label.value_object.identifier import (
            ContactPointLabelIdVO,
        )
        from src.modules.contact_points.infrastructure.normalization.phone import (
            PhoneNormalizer,
        )
        from src.modules.contact_points.infrastructure.persistence import (
            SqlAlchemyContactPointLabelRepository,
        )

        point_id = ContactPointIdVO.from_value(uuid4())
        binding_id = ContactPointBindingIdVO.from_value(uuid4())
        label_id = ContactPointLabelIdVO.from_value(uuid4())
        target = ContactPointTargetVO("crm.contact", EntityIdVO.from_value(uuid4()))
        now = datetime.now(UTC)
        expected = {}
        async with UnitOfWork(self.sessions) as uow:
            points = SqlAlchemyContactPointRepository(uow.session, self.naming)
            bindings = SqlAlchemyContactPointBindingRepository(uow.session, self.naming)
            labels = SqlAlchemyContactPointLabelRepository(uow.session, self.naming)
            for tenant, value, name, time in (
                (self.tenant, "0501234567", "First tenant", now),
                (self.other, "0672222222", "Other tenant", now + timedelta(seconds=1)),
            ):
                actor = EntityIdVO.from_value(uuid4())
                point = ContactPoint.create(
                    point_id=point_id,
                    point_type=ContactPointType.PHONE,
                    normalized=PhoneNormalizer().normalize(
                        value, NormalizationContext("UA")
                    ),
                    actor_id=actor,
                    now=time,
                )
                label = ContactPointLabel.create(
                    label_id=label_id,
                    point_type=ContactPointType.PHONE,
                    name=name,
                    actor_id=actor,
                    now=time,
                )
                binding = ContactPointBinding.create(
                    binding_id=binding_id,
                    point_id=point_id,
                    target=target,
                    label_id=label_id,
                    position=0,
                    actor_id=actor,
                    now=time,
                )
                await labels.add(tenant, label)
                self.assertEqual(await points.get_or_create(tenant, point), point)
                await bindings.replace_for_target(tenant, target, (binding,))
                expected[tenant] = (point, binding, label)

            # The instances and session stay the same while the schema alternates.
            for tenant in (self.tenant, self.other, self.tenant):
                point, binding, label = expected[tenant]
                self.assertEqual(await points.get(tenant, point_id), point)
                self.assertEqual(
                    await points.find_by_canonical(
                        tenant, point.type, point.canonical_value
                    ),
                    point,
                )
                self.assertEqual(
                    await points.get_or_create(
                        tenant, replace(point, id=ContactPointIdVO.from_value(uuid4()))
                    ),
                    point,
                )
                self.assertEqual(await labels.get(tenant, label_id), label)
                self.assertEqual(
                    next(
                        item
                        for item in await labels.list(tenant)
                        if item.id == label_id
                    ),
                    label,
                )
                rows = await bindings.list_for_targets(tenant, (target,))
                self.assertEqual(len(rows), 1)
                self.assertEqual(rows[0].binding, binding)
                self.assertEqual(rows[0].point, point)
                self.assertEqual(
                    await bindings.list_targets(tenant, point_id), (target,)
                )

            self.assertIsNone(
                await points.find_by_canonical(
                    self.other,
                    ContactPointType.PHONE,
                    expected[self.tenant][0].canonical_value,
                )
            )
            label = expected[self.tenant][2]
            label.update(
                name="Renamed",
                is_active=False,
                actor_id=EntityIdVO.from_value(self.actor),
                now=now + timedelta(days=1),
            )
            await labels.save(self.tenant, label)
            self.assertEqual(await labels.get(self.tenant, label_id), label)
            self.assertEqual(
                await labels.get(self.other, label_id), expected[self.other][2]
            )
            await bindings.remove_target(self.tenant, target)
            self.assertEqual(
                await bindings.list_for_targets(self.tenant, (target,)), ()
            )
            self.assertEqual(
                len(await bindings.list_for_targets(self.other, (target,))), 1
            )

    async def test_label_admin_archive_type_and_csrf(self):
        labels = (await self.request("GET", "contact-points/labels")).json()
        self.assertEqual(len(labels), 6)
        label = next(row for row in labels if row["type"] == "phone")
        self.context = replace(
            self.context, principal=replace(self.context.principal, roles=("member",))
        )
        response = await self.request(
            "POST", "contact-points/labels", json={"type": "phone", "name": "New"}
        )
        self.assertEqual(response.status_code, 403)
        self.context = replace(
            self.context, principal=replace(self.context.principal, roles=("admin",))
        )
        response = await self.client.post(
            "/api/console/contact-points/labels",
            json={"type": "phone", "name": "No CSRF"},
        )
        self.assertEqual(response.status_code, 403)
        response = await self.request(
            "PATCH",
            f"contact-points/labels/{label['id']}",
            json={"name": "Archived", "is_active": False},
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertFalse(response.json()["is_active"])
        response = await self.request(
            "POST",
            "contact-points/labels",
            json={"type": "email", "name": "  Support  "},
        )
        self.assertEqual(response.status_code, 201, response.text)
        self.assertEqual(response.json()["name"], "Support")

    async def test_upgrade_existing_crm_and_migration_rollback(self):
        from datetime import UTC, datetime

        contact_id = uuid4()
        async with self.engine.begin() as connection:
            await connection.execute(
                ContactModel.__table__.insert()
                .values(
                    id=contact_id,
                    first_name="Preserved",
                    created_by=self.actor,
                    updated_by=self.actor,
                    created_at=datetime.now(UTC),
                    updated_at=datetime.now(UTC),
                )
                .execution_options(schema_translate_map={"tenant": self.schemas[0]})
            )
        async with self.engine.begin() as connection:
            await TenantMigrator().downgrade(
                connection, self.schemas[0], "0007_crm_contacts_companies"
            )
            await TenantMigrator().upgrade(connection, self.schemas[0])
        async with self.sessions() as session:
            first_name = await session.scalar(
                select(ContactModel.first_name)
                .where(ContactModel.id == contact_id)
                .execution_options(schema_translate_map={"tenant": self.schemas[0]})
            )
        self.assertEqual(first_name, "Preserved")
        self.assertEqual(await self.count(ContactPointLabelModel), 6)
        schema = self.naming.schema_name(EntityIdVO.from_value(uuid4()))
        with self.assertRaisesRegex(RuntimeError, "rollback bootstrap"):
            async with self.engine.begin() as connection:
                await connection.execute(CreateSchema(schema))
                await TenantMigrator().upgrade(connection, schema)
                raise RuntimeError("rollback bootstrap")
        async with self.engine.connect() as connection:
            self.assertFalse(
                await connection.scalar(
                    text(
                        "SELECT EXISTS (SELECT FROM pg_namespace WHERE nspname=:schema)"
                    ),
                    {"schema": schema},
                )
            )


if __name__ == "__main__":
    unittest.main()
