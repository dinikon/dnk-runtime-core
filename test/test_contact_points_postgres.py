"""Real HTTP/DI/PostgreSQL integration; requires an explicitly disposable database."""

import asyncio
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
from src.modules.crm.presentation.http.router import router as crm_router
from src.modules.identity.presentation.http.csrf import issue_csrf
from src.modules.shared.presentation.identity_context.depends import (
    require_authenticated_request_context,
)
from src.modules.shared.domain.identity_context import Principal, RequestContext
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
    ContactPointModel,
    ContactPointBindingModel,
    ContactPointLabelModel,
)
from src.modules.contact_points.infrastructure.persistence.repository.binding_repository import (
    SqlAlchemyContactPointBindingRepository,
)
from src.modules.contact_points.presentation.depends.application import (
    get_resolve_contact_point_targets_use_case,
    get_contact_point_resolver,
)
from src.modules.contact_points.presentation.depends.infrastructure import (
    get_normalizers,
)
from src.modules.contact_points.infrastructure.persistence import (
    SqlAlchemyContactPointRepository,
)
from src.modules.contact_points.application.api import ResolveContactPointTargetsQuery
from src.modules.contact_points.domain.contact_point.value_object.value import (
    ContactPointType,
)
from src.modules.shared.infrastructure.time import UtcClock
from src.modules.crm.infrastructure.persistence import ContactModel

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
        self.app.include_router(crm_router, prefix="/api/console")
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

    async def create(self, *, company=False, **changes):
        path = "crm/companies" if company else "crm/contacts"
        payload = {"name": "Acme"} if company else {"first_name": "Test"}
        payload.update(changes)
        response = await self.request("POST", path, json=payload)
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()

    def phone(self, value="0501234567", **changes):
        return dict(value=value, country_code="UA", **changes)

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
        from src.modules.crm.presentation.depends.infrastructure import (
            ContactRepositoryDep,
            CompanyRepositoryDep,
        )
        from src.modules.contact_points.presentation.depends.infrastructure import (
            ContactPointRepositoryDep,
            ContactPointBindingRepositoryDep,
            ContactPointLabelRepositoryDep,
        )
        from src.modules.shared.presentation.persistence.depends import UoWDep

        @self.app.get("/di-probe")
        async def probe(
            uow: UoWDep,
            contacts: ContactRepositoryDep,
            companies: CompanyRepositoryDep,
            points: ContactPointRepositoryDep,
            bindings: ContactPointBindingRepositoryDep,
            labels: ContactPointLabelRepositoryDep,
        ):
            return {
                "same_session": all(
                    repository.session is uow.session
                    for repository in (contacts, companies)
                )
                and all(
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
            await self.create(
                phones=[self.phone()], emails=[{"value": "test@example.com"}]
            )
        self.assertEqual(len(commits), 1)

    async def test_page_batches_bindings_and_noop_preserves_audit(self):
        contact = await self.create(phones=[self.phone()])
        await self.create(phones=[self.phone("0672222222")])
        calls = []
        original = SqlAlchemyContactPointBindingRepository.list_for_targets

        async def read(repository, tenant_id, targets):
            calls.append(targets)
            return await original(repository, tenant_id, targets)

        with patch.object(
            SqlAlchemyContactPointBindingRepository, "list_for_targets", read
        ):
            response = await self.request("GET", "crm/contacts")
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(len(calls), 1)
        self.assertEqual(len(calls[0]), 2)
        async with self.sessions() as session:
            before = (
                (
                    await session.execute(
                        select(ContactPointBindingModel.__table__).execution_options(
                            schema_translate_map={"tenant": self.schemas[0]}
                        )
                    )
                )
                .mappings()
                .all()
            )
        row = contact["phones"][0]
        response = await self.request(
            "PUT",
            f"crm/contacts/{contact['id']}",
            json={
                "first_name": "Test",
                "phones": [self.phone(binding_id=row["binding_id"])],
            },
        )
        self.assertEqual(response.status_code, 200, response.text)
        async with self.sessions() as session:
            after = (
                (
                    await session.execute(
                        select(ContactPointBindingModel.__table__).execution_options(
                            schema_translate_map={"tenant": self.schemas[0]}
                        )
                    )
                )
                .mappings()
                .all()
            )
        self.assertEqual(before, after)

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

    async def test_shared_phone_rebind_and_delete_preserve_other_owner_and_orphans(
        self,
    ):
        contact = await self.create(phones=[self.phone()])
        company = await self.create(company=True, phones=[self.phone("+380501234567")])
        self.assertEqual(
            contact["phones"][0]["contact_point_id"],
            company["phones"][0]["contact_point_id"],
        )
        self.assertEqual(await self.count(ContactPointModel), 1)
        old_binding = contact["phones"][0]["binding_id"]
        response = await self.request(
            "PUT",
            f"crm/contacts/{contact['id']}",
            json={
                "first_name": "Changed",
                "phones": [self.phone("0672222222", binding_id=old_binding)],
            },
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["phones"][0]["binding_id"], old_binding)
        self.assertNotEqual(
            response.json()["phones"][0]["contact_point_id"],
            company["phones"][0]["contact_point_id"],
        )
        current_company = await self.request("GET", f"crm/companies/{company['id']}")
        self.assertEqual(current_company.json()["phones"], company["phones"])
        self.assertEqual(
            (await self.request("DELETE", f"crm/contacts/{contact['id']}")).status_code,
            204,
        )
        self.assertEqual(await self.count(ContactPointModel), 2)
        self.assertEqual(await self.count(ContactPointBindingModel), 1)
        self.assertEqual(
            (
                await self.request("DELETE", f"crm/companies/{company['id']}")
            ).status_code,
            204,
        )
        self.assertEqual(await self.count(ContactPointBindingModel), 0)
        self.assertEqual(await self.count(ContactPointModel), 2)

    async def test_omitted_empty_noop_and_swap(self):
        contact = await self.create(
            phones=[self.phone(), self.phone("0672222222")],
            emails=[{"value": "Denis@Example.COM"}],
        )
        self.assertEqual(contact["emails"][0]["value"], "Denis@example.com")
        response = await self.request(
            "PUT", f"crm/contacts/{contact['id']}", json={"first_name": "Renamed"}
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["phones"], contact["phones"])
        rows = contact["phones"]
        response = await self.request(
            "PUT",
            f"crm/contacts/{contact['id']}",
            json={
                "first_name": "Renamed",
                "phones": [
                    self.phone(rows[1]["value"], binding_id=rows[0]["binding_id"]),
                    self.phone(rows[0]["value"], binding_id=rows[1]["binding_id"]),
                ],
                "emails": [],
            },
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["emails"], [])
        self.assertEqual(
            response.json()["phones"][0]["binding_id"], rows[0]["binding_id"]
        )
        self.assertEqual(response.json()["phones"][0]["value"], rows[1]["value"])

    async def test_invalid_row_duplicate_and_foreign_binding_roll_back_crm(self):
        response = await self.request(
            "POST",
            "crm/contacts",
            json={
                "first_name": "Never saved",
                "phones": [self.phone()],
                "emails": [{"value": "not-an-email"}],
            },
        )
        self.assertEqual(response.status_code, 422, response.text)
        self.assertEqual(
            response.json()["detail"][0]["loc"], ["body", "emails", 0, "value"]
        )
        self.assertEqual(await self.count(ContactModel), 0)
        self.assertEqual(await self.count(ContactPointModel), 0)
        contact = await self.create(phones=[self.phone()])
        response = await self.request(
            "PUT",
            f"crm/contacts/{contact['id']}",
            json={
                "first_name": "Must rollback",
                "phones": [self.phone(), self.phone("+380501234567")],
            },
        )
        self.assertEqual(response.status_code, 422, response.text)
        self.assertEqual(
            (await self.request("GET", f"crm/contacts/{contact['id']}")).json()[
                "first_name"
            ],
            "Test",
        )
        response = await self.request(
            "POST",
            "crm/companies",
            json={
                "name": "Never saved",
                "phones": [self.phone(binding_id=contact["phones"][0]["binding_id"])],
            },
        )
        self.assertEqual(response.status_code, 422, response.text)

    async def test_failure_after_binding_write_rolls_back_all_tables(self):
        original = SqlAlchemyContactPointBindingRepository.replace_for_target

        async def fail_after_write(repository, *args):
            await original(repository, *args)
            raise RuntimeError("injected persistence failure")

        with patch.object(
            SqlAlchemyContactPointBindingRepository,
            "replace_for_target",
            fail_after_write,
        ):
            with self.assertRaisesRegex(RuntimeError, "injected"):
                await self.request(
                    "POST",
                    "crm/contacts",
                    json={"first_name": "Never saved", "phones": [self.phone()]},
                )
        self.assertEqual(await self.count(ContactModel), 0)
        self.assertEqual(await self.count(ContactPointModel), 0)
        self.assertEqual(await self.count(ContactPointBindingModel), 0)

    async def test_tenant_isolation_even_with_identical_record_ids(self):
        contact = await self.create(phones=[self.phone()])
        self.context = replace(
            self.context,
            principal=replace(self.context.principal, tenant_id=str(self.other)),
        )
        self.assertEqual(
            (await self.request("GET", f"crm/contacts/{contact['id']}")).status_code,
            404,
        )
        other_contact = await self.create(phones=[self.phone()])
        self.assertNotEqual(
            contact["phones"][0]["contact_point_id"],
            other_contact["phones"][0]["contact_point_id"],
        )
        # Same owner UUID in a different schema must still address only that schema.
        async with self.engine.begin() as connection:
            from uuid import UUID

            await connection.execute(
                ContactModel.__table__.insert()
                .values(
                    id=UUID(contact["id"]),
                    first_name="Other tenant",
                    created_by=self.actor,
                    updated_by=self.actor,
                )
                .execution_options(schema_translate_map={"tenant": self.schemas[1]})
            )
        response = await self.request("GET", f"crm/contacts/{contact['id']}")
        self.assertEqual(response.json()["first_name"], "Other tenant")
        self.assertEqual(response.json()["phones"], [])
        self.assertEqual(await self.count(ContactPointModel, self.tenant), 1)
        self.assertEqual(await self.count(ContactPointModel, self.other), 1)

    async def test_label_admin_archive_type_and_csrf(self):
        labels = (await self.request("GET", "contact-points/labels")).json()
        self.assertEqual(len(labels), 6)
        label = next(row for row in labels if row["type"] == "phone")
        email_label = next(row for row in labels if row["type"] == "email")
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
        contact = await self.create(phones=[self.phone(label_id=label["id"])])
        response = await self.request(
            "PATCH",
            f"contact-points/labels/{label['id']}",
            json={"name": "Archived", "is_active": False},
        )
        self.assertEqual(response.status_code, 200, response.text)
        row = contact["phones"][0]
        response = await self.request(
            "PUT",
            f"crm/contacts/{contact['id']}",
            json={
                "first_name": "Test",
                "phones": [
                    self.phone(binding_id=row["binding_id"], label_id=label["id"])
                ],
            },
        )
        self.assertEqual(response.status_code, 200, response.text)
        for label_id in (label["id"], email_label["id"]):
            response = await self.request(
                "POST",
                "crm/contacts",
                json={
                    "first_name": "Never saved",
                    "phones": [self.phone(label_id=label_id)],
                },
            )
            self.assertEqual(response.status_code, 422, response.text)
        response = await self.request(
            "POST",
            "contact-points/labels",
            json={"type": "email", "name": "  Support  "},
        )
        self.assertEqual(response.status_code, 201, response.text)
        self.assertEqual(response.json()["name"], "Support")

    async def test_concurrent_resolve_and_owner_updates(self):
        contacts = await asyncio.gather(
            *(self.create(phones=[self.phone()]) for _ in range(4))
        )
        self.assertEqual(await self.count(ContactPointModel), 1)
        self.assertEqual(await self.count(ContactPointBindingModel), 4)
        contact = contacts[0]
        updates = await asyncio.gather(
            *(
                self.request(
                    "PUT",
                    f"crm/contacts/{contact['id']}",
                    json={"first_name": "Test", "phones": [self.phone(value)]},
                )
                for value in ("0672222222", "0501234567")
            )
        )
        self.assertTrue(
            all(response.status_code == 200 for response in updates),
            [r.text for r in updates],
        )
        self.assertEqual(await self.count(ContactPointBindingModel), 4)
        # Race a replacement against delete; replacement either wins first or sees a missing owner.
        update, deleted = await asyncio.gather(
            self.request(
                "PUT",
                f"crm/contacts/{contact['id']}",
                json={"first_name": "Test", "phones": [self.phone()]},
            ),
            self.request("DELETE", f"crm/contacts/{contact['id']}"),
        )
        self.assertIn(update.status_code, (200, 404))
        self.assertEqual(deleted.status_code, 204, deleted.text)
        self.assertEqual(await self.count(ContactPointBindingModel), 3)

    async def test_reverse_lookup_is_read_only(self):
        contact = await self.create(phones=[self.phone()])
        async with UnitOfWork(self.sessions) as uow:
            points = SqlAlchemyContactPointRepository(uow.session, self.naming)
            bindings = SqlAlchemyContactPointBindingRepository(uow.session, self.naming)
            resolver = get_contact_point_resolver(points, get_normalizers(), UtcClock())
            use_case = get_resolve_contact_point_targets_use_case(
                resolver, points, bindings
            )
            result = await use_case(
                ResolveContactPointTargetsQuery(
                    self.tenant, ContactPointType.PHONE, "0501234567", "UA"
                )
            )
            self.assertEqual(str(result[0].record_id), contact["id"])
            self.assertEqual(result[0].model_key, "crm.contact")
            self.assertEqual(
                await use_case(
                    ResolveContactPointTargetsQuery(
                        self.tenant, ContactPointType.EMAIL, "missing@example.com"
                    )
                ),
                (),
            )
        self.assertEqual(await self.count(ContactPointModel), 1)

    async def test_upgrade_existing_crm_and_migration_rollback(self):
        contact = await self.create()
        async with self.engine.begin() as connection:
            await TenantMigrator().downgrade(
                connection, self.schemas[0], "0007_crm_contacts_companies"
            )
            await TenantMigrator().upgrade(connection, self.schemas[0])
        response = await self.request("GET", f"crm/contacts/{contact['id']}")
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["phones"], [])
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
