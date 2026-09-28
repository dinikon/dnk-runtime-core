"""Real request/UoW/migration/concurrency checks on a disposable PostgreSQL."""

import asyncio
from dataclasses import replace
from unittest.mock import patch
from uuid import uuid4

from httpx import ASGITransport, AsyncClient
from sqlalchemy import insert, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from test import test_contact_points_postgres as support
from src.modules.crm.infrastructure.persistence.models import (
    ContactCompanyModel,
    ContactModel,
    CompanyModel,
)
from src.modules.crm.infrastructure.persistence.contact_repository import (
    SqlAlchemyContactRepository,
)
from src.modules.shared.infrastructure.persistence.tenant_migrations import (
    TenantMigrator,
)


class CrmRelationsPostgresTests(support.ContactPointsPostgresTests):
    # Reuse the established isolated tenant/HTTP fixture and its contact-point regressions.
    async def detail(self, kind, identifier):
        response = await self.request("GET", f"crm/{kind}/{identifier}")
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    async def link_contact(self, contact, companies, *, expected=None, **changes):
        payload = {
            "first_name": contact["first_name"],
            "company_ids": [item["id"] for item in companies],
            "expected_company_ids": [
                item["id"]
                for item in (
                    contact.get("companies", []) if expected is None else expected
                )
            ],
        }
        payload.update(changes)
        return await self.request("PUT", f"crm/contacts/{contact['id']}", json=payload)

    async def link_company(self, company, contacts, *, expected=None, **changes):
        payload = {
            "name": company["name"],
            "contact_ids": [item["id"] for item in contacts],
            "expected_contact_ids": [
                item["id"]
                for item in (
                    company.get("contacts", []) if expected is None else expected
                )
            ],
        }
        payload.update(changes)
        return await self.request("PUT", f"crm/companies/{company['id']}", json=payload)

    async def test_create_both_directions_unlink_and_preserve_other_companies(self):
        a = await self.create(company=True, name="A")
        b = await self.create(company=True, name="B")
        c = await self.create(company_ids=[a["id"], b["id"]])
        self.assertEqual([item["id"] for item in c["companies"]], [a["id"], b["id"]])
        self.assertEqual(
            (await self.detail("companies", a["id"]))["contacts"][0]["id"], c["id"]
        )
        d = await self.create(first_name="Second")
        added = await self.create(
            company=True, name="New", contact_ids=[c["id"], d["id"]]
        )
        self.assertEqual(len(added["contacts"]), 2)
        response = await self.link_company(added, [])
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(len((await self.detail("contacts", c["id"]))["companies"]), 2)
        self.assertEqual((await self.detail("contacts", d["id"]))["companies"], [])
        current = await self.detail("contacts", c["id"])
        response = await self.link_contact(current, [])
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(await self.count(ContactCompanyModel), 0)
        self.assertEqual(await self.count(CompanyModel), 3)

    async def test_omitted_null_missing_expected_and_duplicate_arrays(self):
        a = await self.create(company=True)
        c = await self.create(company_ids=[a["id"]])
        response = await self.request(
            "PUT", f"crm/contacts/{c['id']}", json={"first_name": "New name"}
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(len(response.json()["companies"]), 1)
        for payload in (
            {"company_ids": None},
            {"company_ids": []},
            {"expected_company_ids": []},
            {"company_ids": [a["id"], a["id"]], "expected_company_ids": [a["id"]]},
        ):
            response = await self.request(
                "PUT",
                f"crm/contacts/{c['id']}",
                json={"first_name": "Must roll back", **payload},
            )
            self.assertEqual(response.status_code, 422, response.text)
        for field in ("company_ids", "expected_company_ids"):
            response = await self.request(
                "PUT",
                f"crm/contacts/{c['id']}",
                json={
                    "first_name": "Bad",
                    "company_ids": [],
                    "expected_company_ids": [a["id"]],
                    field: None,
                },
            )
            self.assertEqual(response.status_code, 422)
        response = await self.request(
            "POST",
            "crm/companies",
            json={"name": "Duplicate", "contact_ids": [c["id"], c["id"]]},
        )
        self.assertEqual(response.status_code, 422, response.text)
        self.assertEqual(await self.count(CompanyModel), 1)
        self.assertEqual(
            (await self.detail("contacts", c["id"]))["first_name"], "New name"
        )

    async def test_stale_snapshot_rolls_back_names_points_and_links(self):
        a = await self.create(company=True)
        b = await self.create(company=True, name="B")
        c = await self.create()
        self.assertEqual((await self.link_contact(c, [a])).status_code, 200)
        response = await self.link_contact(
            c, [b], first_name="Lost", phones=[self.phone()]
        )
        self.assertEqual(response.status_code, 409, response.text)
        fresh = await self.detail("contacts", c["id"])
        self.assertEqual(fresh["first_name"], c["first_name"])
        self.assertEqual(fresh["phones"], [])
        self.assertEqual([item["id"] for item in fresh["companies"]], [a["id"]])
        response = await self.link_company(
            a, [], name="Lost", emails=[{"value": "lost@example.com"}]
        )
        self.assertEqual(response.status_code, 409, response.text)
        self.assertEqual((await self.detail("companies", a["id"]))["name"], a["name"])

    async def test_available_candidates_filter_before_count_and_pagination(self):
        companies = [
            await self.create(company=True, name=f"Company {index}")
            for index in range(4)
        ]
        c = await self.create(company_ids=[companies[0]["id"], companies[2]["id"]])
        path = f"crm/contacts/{c['id']}/available-companies?q=Company&limit=1"
        first = await self.request("GET", path)
        second = await self.request("GET", path + "&offset=1")
        self.assertEqual(first.status_code, 200, first.text)
        self.assertEqual(first.json()["total"], 2)
        self.assertEqual(first.json()["items"][0]["id"], companies[1]["id"])
        self.assertEqual(second.json()["items"][0]["id"], companies[3]["id"])
        other = await self.create(first_name="Available")
        response = await self.request(
            "GET", f"crm/companies/{companies[0]['id']}/available-contacts"
        )
        self.assertEqual(response.json()["total"], 1)
        self.assertEqual(response.json()["items"][0]["id"], other["id"])
        self.assertEqual(
            (
                await self.request("GET", f"crm/contacts/{uuid4()}/available-companies")
            ).status_code,
            404,
        )

    async def test_reads_do_not_reconstruct_crm_aggregates(self):
        c = await self.create()
        with patch(
            "src.modules.crm.infrastructure.persistence.contact_repository.contact_entity",
            side_effect=AssertionError("domain read"),
        ):
            await self.detail("contacts", c["id"])
            response = await self.request("GET", "crm/contacts")
            self.assertEqual(response.status_code, 200)

    async def test_link_only_change_updates_contact_audit_and_noop_preserves_it(self):
        a = await self.create(company=True)
        c = await self.create()
        linked = (await self.link_contact(c, [a])).json()
        self.assertGreater(linked["updated_at"], c["updated_at"])
        noop = (await self.link_contact(linked, [a])).json()
        self.assertEqual(noop["updated_at"], linked["updated_at"])

    async def test_foreign_targets_and_identical_ids_are_isolated(self):
        a = await self.create(company=True, name="Tenant A")
        c = await self.create(company_ids=[a["id"]])
        original = self.context
        self.context = replace(
            self.context,
            principal=replace(self.context.principal, tenant_id=str(self.other.uuid)),
        )
        foreign = await self.create(company=True, name="Tenant B only")
        b_contact = await self.create()
        response = await self.link_contact(b_contact, [a])
        self.assertEqual(response.status_code, 404)
        self.assertEqual(
            (
                await self.request("GET", f"crm/contacts/{c['id']}/available-companies")
            ).status_code,
            404,
        )
        # Same UUIDs in both schemas must still represent independent aggregates.
        async with self.sessions() as session, session.begin():
            for model, record in ((ContactModel, c), (CompanyModel, a)):
                source = model.__table__
                row = (
                    (
                        await session.execute(
                            select(source)
                            .where(source.c.id == record["id"])
                            .execution_options(
                                schema_translate_map={"tenant": self.schemas[0]}
                            )
                        )
                    )
                    .mappings()
                    .one()
                )
                await session.execute(
                    insert(source)
                    .values(dict(row))
                    .execution_options(schema_translate_map={"tenant": self.schemas[1]})
                )
        duplicate = await self.detail("contacts", c["id"])
        self.assertEqual(duplicate["companies"], [])
        self.assertEqual(
            (await self.link_contact(duplicate, [foreign])).status_code, 200
        )
        self.context = original
        unchanged = await self.detail("contacts", c["id"])
        self.assertEqual([item["id"] for item in unchanged["companies"]], [a["id"]])
        response = await self.link_contact(unchanged, [foreign])
        self.assertEqual(response.status_code, 404)

    async def test_failure_after_partial_links_rolls_back_company_and_all_contacts(
        self,
    ):
        contacts = [await self.create(first_name=str(index)) for index in range(2)]
        original = SqlAlchemyContactRepository.save
        count = 0

        async def fail_second(repository, tenant_id, contact):
            nonlocal count
            await original(repository, tenant_id, contact)
            count += 1
            if count == 2:
                raise RuntimeError("injected link failure")

        async with AsyncClient(
            transport=ASGITransport(app=self.app, raise_app_exceptions=False),
            base_url="https://tenant.example",
            cookies=self.client.cookies,
        ) as client:
            with patch.object(SqlAlchemyContactRepository, "save", fail_second):
                response = await client.post(
                    "/api/console/crm/companies",
                    json={
                        "name": "Rollback",
                        "contact_ids": [item["id"] for item in contacts],
                        "phones": [self.phone()],
                    },
                    headers=self.headers,
                )
        self.assertEqual(response.status_code, 500)
        self.assertEqual(await self.count(CompanyModel), 0)
        self.assertEqual(await self.count(ContactCompanyModel), 0)
        for contact in contacts:
            self.assertEqual(
                (await self.detail("contacts", contact["id"]))["updated_at"],
                contact["updated_at"],
            )

    async def test_failure_after_points_and_links_rolls_back_whole_card(self):
        a = await self.create(company=True)
        with patch(
            "src.modules.crm.application.contact.use_case.get_contact.GetContactUseCase.__call__",
            side_effect=RuntimeError("response projection failure"),
        ):
            async with AsyncClient(
                transport=ASGITransport(app=self.app, raise_app_exceptions=False),
                base_url="https://tenant.example",
                cookies=self.client.cookies,
            ) as client:
                response = await client.post(
                    "/api/console/crm/contacts",
                    json={
                        "first_name": "Rollback",
                        "company_ids": [a["id"]],
                        "phones": [self.phone()],
                    },
                    headers=self.headers,
                )
        self.assertEqual(response.status_code, 500)
        self.assertEqual(await self.count(ContactModel), 0)
        self.assertEqual(await self.count(ContactCompanyModel), 0)
        self.assertEqual(await self.count(support.ContactPointModel), 0)
        self.assertEqual(await self.count(support.ContactPointBindingModel), 0)

    async def test_commit_failure_rolls_back_card_after_response(self):
        a = await self.create(company=True)
        async with AsyncClient(
            transport=ASGITransport(app=self.app, raise_app_exceptions=False),
            base_url="https://tenant.example",
            cookies=self.client.cookies,
        ) as client:
            with patch.object(
                AsyncSession,
                "commit",
                side_effect=RuntimeError("injected commit failure"),
            ):
                response = await client.post(
                    "/api/console/crm/contacts",
                    json={
                        "first_name": "Rollback",
                        "company_ids": [a["id"]],
                        "phones": [self.phone()],
                    },
                    headers=self.headers,
                )
        # The original request-scoped UoW commits after the response is sent.
        self.assertEqual(response.status_code, 201, response.text)
        self.assertEqual(await self.count(ContactModel), 0)
        self.assertEqual(await self.count(ContactCompanyModel), 0)
        self.assertEqual(await self.count(support.ContactPointModel), 0)

    async def test_competing_opposite_card_updates_have_one_winner(self):
        a = await self.create(company=True)
        c = await self.create()
        replies = await asyncio.wait_for(
            asyncio.gather(self.link_contact(c, [a]), self.link_company(a, [c])), 10
        )
        self.assertEqual(
            sorted(reply.status_code for reply in replies),
            [200, 409],
            [r.text for r in replies],
        )
        self.assertEqual(await self.count(ContactCompanyModel), 1)

    async def test_overlapping_company_batches_preserve_both_memberships(self):
        a, b = await self.create(company=True, name="A"), await self.create(
            company=True, name="B"
        )
        contacts = [await self.create(first_name=str(index)) for index in range(3)]
        replies = await asyncio.wait_for(
            asyncio.gather(
                self.link_company(a, contacts),
                self.link_company(b, list(reversed(contacts))),
            ),
            10,
        )
        self.assertEqual(
            [r.status_code for r in replies], [200, 200], [r.text for r in replies]
        )
        self.assertEqual(await self.count(ContactCompanyModel), 6)

    async def test_link_racing_company_deletion_never_orphans(self):
        a = await self.create(company=True)
        c = await self.create()
        replies = await asyncio.wait_for(
            asyncio.gather(
                self.link_contact(c, [a]),
                self.request("DELETE", f"crm/companies/{a['id']}"),
            ),
            10,
        )
        self.assertIn(replies[0].status_code, (200, 404))
        self.assertIn(replies[1].status_code, (204, 409))
        remaining = await self.count(CompanyModel)
        self.assertEqual(await self.count(ContactCompanyModel), remaining)

    async def test_deletion_unlinks_without_deleting_opposite_objects(self):
        a, b = await self.create(company=True, name="A"), await self.create(
            company=True, name="B"
        )
        c = await self.create(company_ids=[a["id"], b["id"]], phones=[self.phone()])
        response = await self.request("DELETE", f"crm/companies/{a['id']}")
        self.assertEqual(response.status_code, 204, response.text)
        remaining = await self.detail("contacts", c["id"])
        self.assertEqual([item["id"] for item in remaining["companies"]], [b["id"]])
        self.assertEqual(len(remaining["phones"]), 1)
        self.assertEqual(
            (await self.request("DELETE", f"crm/contacts/{c['id']}")).status_code, 204
        )
        self.assertEqual(await self.count(ContactCompanyModel), 0)
        self.assertEqual(await self.count(CompanyModel), 1)

    async def test_database_unique_foreign_keys_and_migration_roundtrip(self):
        a = await self.create(company=True)
        c = await self.create(company_ids=[a["id"]])
        for company_id in (a["id"], str(uuid4())):
            with self.assertRaises(IntegrityError):
                async with self.sessions() as session, session.begin():
                    await session.execute(
                        insert(ContactCompanyModel.__table__)
                        .values(contact_id=c["id"], company_id=company_id)
                        .execution_options(
                            schema_translate_map={"tenant": self.schemas[0]}
                        )
                    )
        async with self.engine.begin() as connection:
            await TenantMigrator().downgrade(
                connection, self.schemas[0], "0008_contact_points"
            )
            await TenantMigrator().upgrade(connection, self.schemas[0])
            await TenantMigrator().upgrade(connection, self.schemas[0])
        self.assertEqual(await self.count(ContactCompanyModel), 0)
        self.assertEqual(await self.count(ContactModel), 1)
        self.assertEqual(await self.count(CompanyModel), 1)

    async def test_relation_query_and_command_dependencies_share_one_session(self):
        from src.modules.crm.presentation.depends.infrastructure import (
            ContactRepositoryDep,
            CompanyRepositoryDep,
            ContactQueryRepositoryDep,
            CompanyQueryRepositoryDep,
        )
        from src.modules.shared.presentation.persistence.depends import UoWDep

        @self.app.get("/relation-di-probe")
        async def probe(
            uow: UoWDep,
            contacts: ContactRepositoryDep,
            companies: CompanyRepositoryDep,
            contact_queries: ContactQueryRepositoryDep,
            company_queries: CompanyQueryRepositoryDep,
        ):
            return {
                "shared": all(
                    repo.session is uow.session
                    for repo in (contacts, companies, contact_queries, company_queries)
                )
            }

        self.assertEqual(
            (await self.client.get("/relation-di-probe")).json(), {"shared": True}
        )

    async def test_link_racing_contact_deletion_never_orphans(self):
        a = await self.create(company=True)
        c = await self.create()
        replies = await asyncio.wait_for(
            asyncio.gather(
                self.link_company(a, [c]),
                self.request("DELETE", f"crm/contacts/{c['id']}"),
            ),
            10,
        )
        self.assertIn(replies[0].status_code, (200, 404))
        self.assertEqual(replies[1].status_code, 204)
        self.assertEqual(await self.count(ContactCompanyModel), 0)
        self.assertEqual(await self.count(CompanyModel), 1)
