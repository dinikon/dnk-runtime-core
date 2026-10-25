"""Сквозные HTTP-проверки единой продажи и атомарной конвертации на PostgreSQL."""

import asyncio
import unittest
from dataclasses import replace
from unittest.mock import Mock
from uuid import uuid4
from test import test_crm_company_postgres as company_tests

TEST_URL = company_tests.TEST_URL
from src.modules.crm.presentation.lead.router import router as leads
from src.modules.crm.presentation.deal.router import router as deals
from src.modules.crm.presentation.sales.router import router as sales
from src.modules.funnel.presentation.router import router as funnels
from src.modules.crm.infrastructure.persistence.models.contact import ContactModel
from src.modules.crm.infrastructure.persistence.models.company import CompanyModel
from src.modules.crm.infrastructure.persistence.models.deal import DealModel


@unittest.skipUnless(TEST_URL, "Требуется отдельная TEST_POSTGRES_URL.")
class CrmSalesPostgresTests(unittest.IsolatedAsyncioTestCase):
    rows = company_tests.CompanyPostgresTests.rows

    async def asyncSetUp(self) -> None:
        """Создаёт изолированные tenant-схемы с реальными UoW и CSRF."""
        await company_tests.CompanyPostgresTests.asyncSetUp(self)
        self.app.state.uuid_generator = Mock(new=Mock(side_effect=uuid4))
        for router in (leads, deals, sales, funnels):
            self.app.include_router(router, prefix="/api/console")

    async def asyncTearDown(self) -> None:
        """Удаляет только схемы и соединения текущего теста."""
        await company_tests.CompanyPostgresTests.asyncTearDown(self)

    async def create_lead(self) -> dict:
        """Создаёт лид с точной предварительной корзиной."""
        response = await self.client.post(
            "/api/console/crm/leads",
            headers=self.headers,
            json=dict(
                title="Монтаж",
                first_name="Іван",
                company_name="Компанія",
                basket=dict(
                    currency="UAH",
                    items=[
                        dict(
                            client_line_key="line",
                            name="Работа",
                            kind="service",
                            quantity="1.5",
                            unit_price="10.01",
                        )
                    ],
                ),
            ),
        )
        self.assertEqual(response.status_code, 201, response.text)
        detail = await self.client.get(
            "/api/console/crm/leads/" + response.json()["id"]
        )
        self.assertEqual(detail.status_code, 200, detail.text)
        return detail.json()

    async def conversion(
        self, lead: dict, mode: str = "contact_company_deal", key: str = "replay"
    ) -> tuple[str, dict, dict]:
        """Готовит актуальный payload и ключ конкретной конвертации."""
        path = "/api/console/crm/leads/" + lead["id"]
        context = await self.client.get(path + "/conversion-context")
        self.assertEqual(context.status_code, 200, context.text)
        body = dict(
            mode=mode,
            expected_source_token=context.json()["source_token"],
            expected_basket_revision=lead["basket"]["revision"],
        )
        selected = mode.split("_")
        for kind in ("contact", "company", "deal"):
            if kind in selected:
                body[kind + "_points"] = []
        return path, body, dict(self.headers, **{"Idempotency-Key": key})

    async def test_all_seven_modes_and_readonly_source(self) -> None:
        """Проверяет матрицу семи режимов, replay и read-only источник."""
        for mode in (
            "contact",
            "company",
            "contact_company",
            "contact_deal",
            "company_deal",
            "contact_company_deal",
            "deal",
        ):
            lead = await self.create_lead()
            self.assertEqual(lead["basket"]["total"], "15.02")
            path, body, headers = await self.conversion(lead, mode, key=str(uuid4()))
            response = await self.client.post(
                path + "/convert", headers=headers, json=body
            )
            self.assertEqual(response.status_code, 200, response.text)
            result = response.json()
            for kind in ("contact", "company", "deal"):
                self.assertEqual(
                    result[kind + "_id"] is not None, kind in mode.split("_")
                )
            replay = await self.client.post(
                path + "/convert", headers=headers, json=body
            )
            self.assertEqual(replay.status_code, 200, replay.text)
            self.assertTrue(replay.json()["replay"])
            source = (await self.client.get(path)).json()
            self.assertEqual(source["basket"]["state"], "frozen")
            blocked = await self.client.patch(
                path, headers=self.headers, json={"title": "Нельзя"}
            )
            self.assertEqual(blocked.status_code, 409, blocked.text)
            if result["deal_id"]:
                deal = await self.client.get(
                    "/api/console/crm/deals/" + result["deal_id"]
                )
                self.assertEqual(deal.status_code, 200, deal.text)
                self.assertEqual(deal.json()["lifecycle_state"], "draft")
                self.assertNotEqual(deal.json()["basket"]["id"], source["basket"]["id"])
                self.assertNotEqual(
                    deal.json()["basket"]["items"][0]["id"],
                    source["basket"]["items"][0]["id"],
                )
                self.assertEqual(
                    deal.json()["basket"]["total"], source["basket"]["total"]
                )

    async def test_concurrent_replay_and_rollback(self) -> None:
        """Не допускает частичных результатов и двойной конкурентной конвертации."""
        lead = await self.create_lead()
        path, body, headers = await self.conversion(lead)
        bad = dict(body, company={"legal_name": ""})
        response = await self.client.post(path + "/convert", headers=headers, json=bad)
        self.assertEqual(response.status_code, 422, response.text)
        self.assertEqual(await self.rows(ContactModel), [])
        self.assertEqual(await self.rows(CompanyModel), [])
        self.assertEqual(await self.rows(DealModel), [])
        self.assertIsNone((await self.client.get(path)).json()["conversion_result"])
        results = await asyncio.gather(
            *(
                self.client.post(path + "/convert", headers=headers, json=body)
                for _ in range(2)
            )
        )
        for response in results:
            self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(
            results[0].json()["conversion_id"], results[1].json()["conversion_id"]
        )
        self.assertEqual(len(await self.rows(ContactModel)), 1)

    async def test_funnel_revision_transfer_and_isolation(self) -> None:
        """Проверяет перенос, конкурирующую версию и tenant-изоляцию."""
        lead = await self.create_lead()
        response = await self.client.post(
            "/api/console/funnels",
            headers=self.headers,
            json={
                "model_key": "crm.lead",
                "name": "Новая воронка",
                "stages": [
                    {"client_key": "a", "name": "Первый"},
                    {"client_key": "b", "name": "Второй"},
                ],
            },
        )
        self.assertEqual(response.status_code, 201, response.text)
        fid = response.json()["id"]
        funnel = (await self.client.get("/api/console/funnels/" + fid)).json()
        path = "/api/console/crm/leads/" + lead["id"]
        moved = await self.client.put(
            path + "/funnel",
            headers=self.headers,
            json={"funnel_id": fid, "expected_position_revision": 1},
        )
        self.assertEqual(moved.status_code, 200, moved.text)
        self.assertEqual(moved.json()["stage_id"], funnel["stages"][0]["id"])
        stale = await self.client.put(
            path + "/stage",
            headers=self.headers,
            json={
                "stage_id": funnel["stages"][1]["id"],
                "expected_position_revision": 1,
            },
        )
        self.assertEqual(stale.status_code, 409)
        changed = await self.client.put(
            "/api/console/funnels/" + fid,
            headers=self.headers,
            json={
                "name": "Обновлена",
                "expected_revision": 1,
                "stages": [
                    dict(id=s["id"], name=s["name"], color=s["color"])
                    for s in reversed(funnel["stages"])
                ],
            },
        )
        self.assertEqual(changed.status_code, 200, changed.text)
        self.assertEqual(
            (await self.client.get(path)).json()["stage_id"], funnel["stages"][0]["id"]
        )
        self.app.state.test_context = replace(
            self.context,
            principal=replace(self.context.principal, tenant_id=str(self.other)),
        )
        self.assertEqual((await self.client.get(path)).status_code, 404)

    async def test_points_copy_explicit_empty_and_conversion_selection(self) -> None:
        """Собственные bindings и явный выбор Company не меняют исходный Contact."""
        from src.modules.crm.presentation.contact.router import (
            router as contacts_router,
        )

        self.app.include_router(contacts_router, prefix="/api/console")
        created = await self.client.post(
            "/api/console/crm/contacts",
            headers=self.headers,
            json={"first_name": "Исходный"},
        )
        self.assertEqual(created.status_code, 201, created.text)
        cid = created.json()["id"]
        contact_path = "/api/console/crm/contacts/" + cid
        points = await self.client.put(
            contact_path + "/contact-points",
            headers=self.headers,
            json={
                "phones": [{"value": "0501234567", "country_code": "UA"}],
                "emails": [{"value": "client@example.com"}],
            },
        )
        self.assertEqual(points.status_code, 200, points.text)

        async def new_lead(**extra):
            """Создаёт лид из Contact с явными overrides."""
            response = await self.client.post(
                "/api/console/crm/leads",
                headers=self.headers,
                json={
                    "title": "Из контакта",
                    "contact_id": cid,
                    "company_name": "Новая",
                    "basket": {"currency": "EUR"},
                    **extra,
                },
            )
            self.assertEqual(response.status_code, 201, response.text)
            return (
                await self.client.get("/api/console/crm/leads/" + response.json()["id"])
            ).json()

        empty = await new_lead(phones=[], emails=[], first_name=None)
        self.assertIsNone(empty["first_name"])
        self.assertEqual(empty["points"], {"phones": [], "emails": []})
        lead = await new_lead()
        self.assertEqual(lead["first_name"], "Исходный")
        by_contact = await self.client.get(
            "/api/console/crm/leads", params={"search": "Исходный"}
        )
        self.assertEqual(by_contact.status_code, 200, by_contact.text)
        self.assertEqual(
            {row["id"] for row in by_contact.json()["items"]}, {lead["id"], empty["id"]}
        )
        self.assertEqual(lead["points"]["phones"][0]["value"], "+380501234567")
        self.assertNotEqual(
            lead["points"]["phones"][0]["binding_id"],
            points.json()["phones"][0]["binding_id"],
        )
        path, body, headers = await self.conversion(lead)
        phone = lead["points"]["phones"][0]["binding_id"]
        email = lead["points"]["emails"][0]["binding_id"]
        body.update(
            contact_points=[phone, email], company_points=[email], deal_points=[phone]
        )
        result = await self.client.post(path + "/convert", headers=headers, json=body)
        self.assertEqual(result.status_code, 200, result.text)
        company_points = await self.client.get(
            "/api/console/crm/companies/"
            + result.json()["company_id"]
            + "/contact-points"
        )
        self.assertEqual(len(company_points.json()["phones"]), 0)
        self.assertEqual(
            company_points.json()["emails"][0]["value"], "client@example.com"
        )
        self.assertNotEqual(company_points.json()["emails"][0]["binding_id"], email)
        self.assertEqual(
            (await self.client.get(contact_path + "/contact-points")).json(),
            points.json(),
        )
        forbidden = await self.client.put(
            path + "/stage",
            headers=self.headers,
            json={
                "stage_id": lead["stage_id"],
                "expected_position_revision": lead["position_revision"],
            },
        )
        self.assertEqual(forbidden.status_code, 409)
        different = await self.client.post(
            path + "/convert",
            headers=dict(headers, **{"Idempotency-Key": "other"}),
            json=body,
        )
        self.assertEqual(different.status_code, 409)

    async def test_direct_deal_decimal_basket_conflict_and_participants(self) -> None:
        """Дубликаты товара — независимые строки; stale Basket не меняет заголовок."""
        from src.modules.crm.presentation.contact.router import (
            router as contacts_router,
        )

        self.app.include_router(contacts_router, prefix="/api/console")
        contacts = []
        for name in ("Первый", "Второй"):
            response = await self.client.post(
                "/api/console/crm/contacts",
                headers=self.headers,
                json={"first_name": name},
            )
            contacts.append(response.json()["id"])
        response = await self.client.post(
            "/api/console/crm/deals",
            headers=self.headers,
            json={
                "title": "Без лида",
                "contact_ids": contacts,
                "basket": {
                    "currency": "USD",
                    "items": [
                        {
                            "client_line_key": "a",
                            "name": "Строка",
                            "kind": "product",
                            "quantity": "0.125",
                            "unit_price": "0",
                        },
                        {
                            "client_line_key": "b",
                            "name": "Строка",
                            "kind": "product",
                            "quantity": "1.5",
                            "unit_price": "0.01",
                        },
                    ],
                },
            },
        )
        self.assertEqual(response.status_code, 201, response.text)
        path = "/api/console/crm/deals/" + response.json()["id"]
        deal = (await self.client.get(path)).json()
        self.assertIsNone(deal["source_lead_id"])
        self.assertEqual(set(deal["contact_ids"]), set(contacts))
        by_participant = await self.client.get(
            "/api/console/crm/deals", params={"search": "Второй"}
        )
        self.assertEqual(by_participant.status_code, 200, by_participant.text)
        self.assertEqual(by_participant.json()["total"], 1)
        self.assertEqual(by_participant.json()["items"][0]["id"], deal["id"])
        self.assertEqual(deal["basket"]["total"], "0.02")
        lines = [
            {k: v for k, v in i.items() if k not in ("line_total", "position")}
            for i in reversed(deal["basket"]["items"])
        ]
        changed = await self.client.patch(
            path,
            headers=self.headers,
            json={
                "basket": {"currency": "EUR", "expected_revision": 1, "items": lines}
            },
        )
        self.assertEqual(changed.status_code, 200, changed.text)
        stale = await self.client.patch(
            path,
            headers=self.headers,
            json={
                "title": "Нельзя сохранить",
                "basket": {"currency": "UAH", "expected_revision": 1, "items": []},
            },
        )
        self.assertEqual(stale.status_code, 409, stale.text)
        fresh = (await self.client.get(path)).json()
        self.assertEqual(fresh["title"], "Без лида")
        self.assertEqual(fresh["basket"]["currency"], "EUR")
        self.assertEqual(fresh["basket"]["items"][0]["id"], lines[0]["id"])
        invalid = await self.client.patch(
            path, headers=self.headers, json={"lifecycle_state": "completed"}
        )
        self.assertEqual(invalid.status_code, 422)
        missing = await self.client.post(
            "/api/console/crm/deals",
            headers=self.headers,
            json={
                "title": "Ошибка",
                "contact_ids": [str(uuid4())],
                "basket": {"currency": "USD"},
            },
        )
        self.assertEqual(missing.status_code, 404)
        self.assertEqual(len(await self.rows(DealModel)), 1)

    async def test_stale_source_auth_csrf_and_paginated_columns(self) -> None:
        """Контекст устаревает от данных, no-op позиция не увеличивает revision."""
        lead = await self.create_lead()
        path, body, headers = await self.conversion(lead, "deal")
        no_op = await self.client.put(
            path + "/stage",
            headers=self.headers,
            json={"stage_id": lead["stage_id"], "expected_position_revision": 1},
        )
        self.assertEqual(no_op.status_code, 200, no_op.text)
        self.assertEqual(no_op.json()["position_revision"], 1)
        self.assertEqual(
            (
                await self.client.patch(
                    path, headers=self.headers, json={"title": "Обновлён"}
                )
            ).status_code,
            200,
        )
        response = await self.client.post(path + "/convert", headers=headers, json=body)
        self.assertEqual(response.status_code, 409, response.text)
        self.assertEqual(await self.rows(DealModel), [])
        response = await self.client.patch(path, json={"title": "Без CSRF"})
        self.assertEqual(response.status_code, 403)
        for i in range(3):
            await self.create_lead()
        page = await self.client.get(
            "/api/console/crm/leads",
            params={
                "funnel_id": lead["funnel_id"],
                "stage_id": lead["stage_id"],
                "converted": "false",
                "offset": 1,
                "limit": 2,
                "sort": "title",
            },
        )
        self.assertEqual(page.status_code, 200, page.text)
        self.assertEqual(page.json()["total"], 4)
        self.assertEqual(len(page.json()["items"]), 2)
        self.app.state.test_context = replace(self.context, principal=None)
        self.assertEqual((await self.client.get(path)).status_code, 401)
        self.app.state.test_context = self.context

    async def test_catalog_snapshot_is_independent_and_missing_item_rolls_back(
        self,
    ) -> None:
        """Публичный Catalog-контракт копирует тип/SKU, последующее изменение не переоценивает строки."""
        from test.catalog_support import initialize_catalog
        from src.modules.catalog.presentation.router import router as catalog_router
        from src.modules.tenancy.infrastructure.tenant.persistence.tenant_connection import (
            bind_tenant_schema,
        )

        async with self.sessions() as session:
            await bind_tenant_schema(
                await session.connection(), self.tenant.uuid, self.naming
            )
            await initialize_catalog(session, self.tenant, self.actor)
            await session.commit()
        self.app.include_router(catalog_router, prefix="/api/console")
        item = await self.client.post(
            "/api/console/catalog/items",
            headers=self.headers,
            json={"virtual": True, "sku": "SERVICE-001"},
        )
        self.assertEqual(item.status_code, 201, item.text)
        item_id = item.json()["id"]
        rows = [
            dict(
                client_line_key=str(i),
                catalog_item_id=item_id,
                name="Снимок",
                kind="product",
                quantity="0.5",
                unit_price="1.01",
            )
            for i in range(2)
        ]
        created = await self.client.post(
            "/api/console/crm/deals",
            headers=self.headers,
            json={"title": "Каталог", "basket": {"currency": "EUR", "items": rows}},
        )
        self.assertEqual(created.status_code, 201, created.text)
        path = "/api/console/crm/deals/" + created.json()["id"]
        first = (await self.client.get(path)).json()
        self.assertEqual(first["basket"]["total"], "1.02")
        self.assertEqual(first["basket"]["items"][0]["kind"], "service")
        self.assertEqual(first["basket"]["items"][0]["sku"], "SERVICE-001")
        changed = await self.client.patch(
            "/api/console/catalog/items/" + item_id,
            headers=self.headers,
            json={"virtual": False, "sku": "PRODUCT-002"},
        )
        self.assertEqual(changed.status_code, 200, changed.text)
        self.assertEqual(
            (await self.client.get(path)).json()["basket"], first["basket"]
        )
        rows[0]["catalog_item_id"] = str(uuid4())
        missing = await self.client.post(
            "/api/console/crm/deals",
            headers=self.headers,
            json={
                "title": "Не сохранить",
                "basket": {"currency": "EUR", "items": rows},
            },
        )
        self.assertEqual(missing.status_code, 404, missing.text)
        self.assertEqual(len(await self.rows(DealModel)), 1)

    async def test_incremental_migration_preserves_existing_crm(self) -> None:
        """Продолжает populated baseline, сохраняя Contact/Company, отношения и points."""
        from src.modules.crm.presentation.contact.router import router as contact_router
        from src.modules.tenancy.infrastructure.tenant.persistence.tenant_migrations import (
            TenantMigrator,
        )

        self.app.include_router(contact_router, prefix="/api/console")
        contact = await self.client.post(
            "/api/console/crm/contacts",
            headers=self.headers,
            json={"first_name": "Существующий"},
        )
        company = await self.client.post(
            "/api/console/crm/companies",
            headers=self.headers,
            json={"legal_name": "Существующая компания"},
        )
        self.assertEqual(contact.status_code, 201, contact.text)
        self.assertEqual(company.status_code, 201, company.text)
        path = "/api/console/crm/contacts/" + contact.json()["id"]
        linked = await self.client.put(
            path + "/companies/" + company.json()["id"], headers=self.headers
        )
        self.assertEqual(linked.status_code, 204, linked.text)
        points = await self.client.put(
            path + "/contact-points",
            headers=self.headers,
            json={"phones": [], "emails": [{"value": "old@example.com"}]},
        )
        self.assertEqual(points.status_code, 200, points.text)
        migrator = TenantMigrator()
        async with self.engine.begin() as connection:
            await migrator.downgrade(
                connection, self.schemas[0], "0001_tenant_baseline"
            )
            self.assertEqual(
                await migrator.current(connection, self.schemas[0]),
                ("0001_tenant_baseline",),
            )
            await migrator.upgrade(connection, self.schemas[0])
            await migrator.upgrade(connection, self.schemas[0])
            self.assertEqual(
                await migrator.current(connection, self.schemas[0]),
                (migrator.head(),),
            )
        self.assertEqual((await self.client.get(path)).json(), contact.json())
        self.assertEqual(
            (await self.client.get(path + "/contact-points")).json(), points.json()
        )
        self.assertEqual(
            (await self.client.get(path + "/companies")).json()[0]["id"],
            company.json()["id"],
        )
        definitions = await self.client.get("/api/console/funnels")
        self.assertEqual(definitions.status_code, 200, definitions.text)
        self.assertEqual(definitions.json()["total"], 2)
