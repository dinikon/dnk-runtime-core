"""Связи и Draft проверяются настоящими HTTP/CSRF/UoW и PostgreSQL."""

import asyncio
import os
import unittest
from decimal import Decimal
from uuid import UUID, uuid4
from unittest.mock import patch, AsyncMock
from sqlalchemy import select, func, update
from test import test_channels_postgres as fixture_module
from test.catalog_support import initialize_catalog
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.catalog.presentation.router import router as catalog_router
from src.modules.catalog.infrastructure.persistence.models.catalog_item import (
    CatalogItemModel,
)
from src.modules.channels.infrastructure.persistence.models.external_publication import (
    ExternalPublicationModel,
)
from src.modules.channels.infrastructure.persistence.models.external_binding import (
    ExternalBindingModel,
)
from src.modules.channels.application.product_representation.linking_service import (
    PublicationLinkingService,
)
from src.modules.channels.domain.error import ChannelsConflictError


@unittest.skipUnless(
    os.environ.get("TEST_POSTGRES_URL"), "Requires disposable PostgreSQL"
)
class ChannelsBindingsPostgresTests(unittest.IsolatedAsyncioTestCase):
    """Проверяет перенос значений и гонки, не обращаясь к реальным кабинетам."""

    session = fixture_module.ChannelsPostgresTests.session
    request = fixture_module.ChannelsPostgresTests.request
    create = fixture_module.ChannelsPostgresTests.create
    claim = fixture_module.ChannelsPostgresTests.claim
    deliver = fixture_module.ChannelsPostgresTests.deliver
    drain = fixture_module.ChannelsPostgresTests.drain
    asyncTearDown = fixture_module.ChannelsPostgresTests.asyncTearDown

    async def asyncSetUp(self) -> None:
        """Использует реальные сборки Channels и добавляет Catalog HTTP."""
        await fixture_module.ChannelsPostgresTests.asyncSetUp(self)
        self.app.include_router(catalog_router, prefix="/api/console")
        for tenant in (self.tenant, self.other):
            async with self.session(tenant) as session:
                await initialize_catalog(
                    session, EntityIdVO(tenant), EntityIdVO(self.actor)
                )

    async def imported(self, kind: str = "woocommerce") -> tuple[dict, dict]:
        """Возвращает канал и одну из локально загруженных публикаций."""
        channel, connection = await self.create(kind)
        await self.drain()
        page = await self.request(
            "GET", f"/connections/{connection['connection_id']}/publications"
        )
        return channel, page["items"][0]

    def draft(self, publication: dict, sku: str | None = "NEW-SKU") -> dict:
        """Передаёт явные корректные значения, включая обе цены и два названия."""
        return {
            "request_key": str(uuid4()),
            "expected_observed_revision": publication["observed_revision"],
            "values": {
                "titles": {"uk": "Новий товар", "ru": "Новый товар"},
                "sku": sku,
                "regular_price": "123.45",
                "sale_price": "100",
                "currency": "UAH",
                "manage_stock": False,
                "quantity": None,
                "stock_status": (
                    publication["stock_status"]
                    if publication["stock_status"] != "unknown"
                    else "out_of_stock"
                ),
                "backorders": "no",
            },
        }

    async def catalog(
        self, method: str, path: str = "", body: dict | None = None, status: int = 200
    ) -> dict:
        """Вызывает штатные Catalog endpoints с теми же auth/CSRF."""
        response = await self.client.request(
            method, "/api/console/catalog/items" + path, json=body, headers=self.headers
        )
        self.assertEqual(response.status_code, status, response.text)
        return response.json() if status != 204 else {}

    async def item_count(self) -> int:
        """Считает товары одноразового tenant для проверки rollback."""
        async with self.session() as session:
            return await session.scalar(
                select(func.count()).select_from(CatalogItemModel)
            )

    async def test_create_draft_replay_and_no_outbound(self) -> None:
        """Create+bind сохраняет оба перевода/цены и replay переживает новый observed."""
        channel, pub = await self.imported()
        body = self.draft(pub)
        result = await self.request(
            "POST", f"/publications/{pub['publication_id']}/catalog-item", body, 201
        )
        details = await self.catalog("GET", f"/{result['catalog_item_id']}?locale=uk")
        item = details["item"]
        self.assertEqual(item["status"], "draft")
        self.assertEqual(item["content"]["title"], "Новий товар")
        self.assertEqual(
            Decimal(item["price_specification"]["regular_price"]), Decimal("123.45")
        )
        self.assertEqual(
            Decimal(item["price_specification"]["sale_price"]), Decimal("100")
        )
        self.assertEqual(
            (await self.catalog("GET", f"/{result['catalog_item_id']}?locale=ru"))[
                "item"
            ]["content"]["title"],
            "Новый товар",
        )
        async with self.session() as session:
            await session.execute(
                update(ExternalPublicationModel)
                .where(ExternalPublicationModel.id == UUID(pub["publication_id"]))
                .values(observed_revision=pub["observed_revision"] + 1)
            )
        replay = await self.request(
            "POST", f"/publications/{pub['publication_id']}/catalog-item", body, 201
        )
        self.assertEqual(result, replay)
        self.assertEqual(await self.item_count(), 1)
        self.assertFalse(
            (await self.request("GET", f"/{channel['channel_id']}"))["is_enabled"]
        )
        changed = {**body, "values": {**body["values"], "sku": "DIFFERENT"}}
        await self.request(
            "POST", f"/publications/{pub['publication_id']}/catalog-item", changed, 409
        )

    async def test_bind_unbind_preserves_catalog_and_active_filter(self) -> None:
        """Связывание не переносит данные, снятие не удаляет созданный ранее товар."""
        _, pub = await self.imported()
        item = await self.catalog("POST", body={}, status=201)
        bound = await self.request(
            "POST",
            f"/publications/{pub['publication_id']}/binding",
            {"catalog_item_id": item["id"]},
            201,
        )
        before = await self.catalog("GET", f"/{item['id']}?locale=uk")
        self.assertIsNone(before["item"]["sku"])
        self.assertIsNone(before["item"]["content"])
        page = await self.request(
            "GET",
            f"/connections/{pub['connection_id']}/publications?binding_status=bound",
        )
        self.assertEqual(page["total"], 1)
        self.assertEqual(page["items"][0]["catalog_item_id"], item["id"])
        await self.catalog("DELETE", f"/{item['id']}", status=409)
        release = {
            "binding_id": bound["binding_id"],
            "expected_revision": bound["revision"],
        }
        await self.request(
            "DELETE", f"/publications/{pub['publication_id']}/binding", release, 204
        )
        candidates = await self.request(
            "GET", f"/publications/{pub['publication_id']}/catalog-candidates?locale=uk"
        )
        candidate = next(row for row in candidates["items"] if row["id"] == item["id"])
        again = await self.request(
            "POST",
            f"/publications/{pub['publication_id']}/binding",
            {
                "catalog_item_id": item["id"],
                "expected_revision": candidate["representation_revision"],
            },
            201,
        )
        await self.request(
            "DELETE", f"/publications/{pub['publication_id']}/binding", release, 204
        )
        self.assertEqual(
            (
                await self.request(
                    "GET",
                    f"/connections/{pub['connection_id']}/publications?binding_status=bound",
                )
            )["total"],
            1,
        )
        await self.request(
            "DELETE",
            f"/publications/{pub['publication_id']}/binding",
            {"binding_id": again["binding_id"], "expected_revision": again["revision"]},
            204,
        )
        await self.catalog("DELETE", f"/{item['id']}", status=204)

    async def test_create_rollback_if_binding_fails(self) -> None:
        """Не оставляет ни пустой товар, ни receipt при отказе сохранения связи."""
        _, pub = await self.imported()
        body = self.draft(pub)
        with patch.object(
            PublicationLinkingService,
            "attach",
            AsyncMock(side_effect=ChannelsConflictError("test_binding_failure")),
        ):
            await self.request(
                "POST", f"/publications/{pub['publication_id']}/catalog-item", body, 409
            )
        self.assertEqual(await self.item_count(), 0)
        await self.request(
            "POST", f"/publications/{pub['publication_id']}/catalog-item", body, 201
        )
        self.assertEqual(await self.item_count(), 1)

    async def test_concurrent_same_intent_creates_one_item(self) -> None:
        """Два HTTP с одинаковым intent возвращают один завершённый результат."""
        _, pub = await self.imported()
        body = self.draft(pub)
        path = f"/publications/{pub['publication_id']}/catalog-item"
        results = await asyncio.gather(
            self.request("POST", path, body, 201), self.request("POST", path, body, 201)
        )
        self.assertEqual(results[0], results[1])
        self.assertEqual(await self.item_count(), 1)

    async def test_concurrent_different_intents_create_one_item(self) -> None:
        """Разные ключи для одной публикации сериализуются source-lock."""
        _, pub = await self.imported()
        bodies = [self.draft(pub, "A"), self.draft(pub, "B")]
        responses = await asyncio.gather(
            *(
                self.client.post(
                    "/api/console/channels/publications/"
                    + pub["publication_id"]
                    + "/catalog-item",
                    json=body,
                    headers=self.headers,
                )
                for body in bodies
            )
        )
        self.assertEqual(sorted(r.status_code for r in responses), [201, 409])
        self.assertEqual(await self.item_count(), 1)

    async def test_delete_races_with_bind(self) -> None:
        """Невозможно одновременно успешно удалить товар и создать активную ссылку."""
        _, pub = await self.imported()
        item = await self.catalog("POST", body={}, status=201)
        bind, delete = await asyncio.gather(
            self.client.post(
                "/api/console/channels/publications/"
                + pub["publication_id"]
                + "/binding",
                json={"catalog_item_id": item["id"]},
                headers=self.headers,
            ),
            self.client.delete(
                "/api/console/catalog/items/" + item["id"], headers=self.headers
            ),
        )
        self.assertIn((bind.status_code, delete.status_code), ((201, 409), (404, 204)))

    async def test_preview_precision_stock_and_stale_source(self) -> None:
        """Preview показывает ограничения без округления и не создаёт товар."""
        _, pub = await self.imported()
        async with self.session() as session:
            payload = (
                await session.execute(
                    select(ExternalPublicationModel.payload).where(
                        ExternalPublicationModel.id == UUID(pub["publication_id"])
                    )
                )
            ).scalar_one()
            payload["pricing"]["regular"] = "1.1234567"
            payload["stock"] = {"quantity": "1.25", "status": "unknown"}
            await session.execute(
                update(ExternalPublicationModel)
                .where(ExternalPublicationModel.id == UUID(pub["publication_id"]))
                .values(payload=payload)
            )
        preview = await self.request(
            "GET",
            f"/publications/{pub['publication_id']}/catalog-draft-preview?locale=uk&expected_observed_revision={pub['observed_revision']}",
        )
        self.assertTrue(preview["issues"])
        self.assertEqual(
            Decimal(preview["values"]["regular_price"]), Decimal("1.1234567")
        )
        self.assertEqual(await self.item_count(), 0)
        body = self.draft(pub)
        body["values"]["regular_price"] = "1.1234567"
        await self.request(
            "POST", f"/publications/{pub['publication_id']}/catalog-item", body, 422
        )
        body["values"]["regular_price"] = "123.45"
        body["expected_observed_revision"] += 1
        await self.request(
            "POST", f"/publications/{pub['publication_id']}/catalog-item", body, 409
        )

    async def test_sku_collision_occupancy_and_import_do_not_overwrite(self) -> None:
        """SKU не объединяет товары, занятая цель недоступна, импорт не меняет Catalog."""
        _, first = await self.imported()
        page = await self.request(
            "GET", f"/connections/{first['connection_id']}/publications"
        )
        second = page["items"][1]
        result = await self.request(
            "POST",
            f"/publications/{first['publication_id']}/catalog-item",
            self.draft(first),
            201,
        )
        await self.request(
            "POST",
            f"/publications/{second['publication_id']}/catalog-item",
            self.draft(second),
            422,
        )
        candidates = await self.request(
            "GET",
            f"/publications/{second['publication_id']}/catalog-candidates?locale=uk",
        )
        row = next(
            i for i in candidates["items"] if i["id"] == result["catalog_item_id"]
        )
        self.assertFalse(row["can_bind"])
        await self.request(
            "POST",
            f"/publications/{second['publication_id']}/binding",
            {
                "catalog_item_id": result["catalog_item_id"],
                "expected_revision": row["representation_revision"],
            },
            409,
        )
        self.transport.price = "500"
        await self.request(
            "POST",
            f"/connections/{first['connection_id']}/initialization",
            {"request_key": str(uuid4())},
            202,
        )
        await self.drain()
        details = await self.catalog("GET", f"/{result['catalog_item_id']}?locale=uk")
        self.assertEqual(
            Decimal(details["item"]["price_specification"]["regular_price"]),
            Decimal("123.45"),
        )
        self.assertEqual(
            (
                await self.request(
                    "GET",
                    f"/connections/{first['connection_id']}/publications?binding_status=bound",
                )
            )["total"],
            1,
        )

    async def test_tenant_and_catalog_create_authorization_are_enforced(self) -> None:
        """Запрос не может создать товар в чужом tenant или обойти Catalog permission."""
        from dataclasses import replace
        from types import SimpleNamespace
        from src.modules.identity.presentation.access.depends import (
            get_authorization_service,
        )

        _, pub = await self.imported()
        body = self.draft(pub)
        original = self.app.state.test_context
        self.app.state.test_context = replace(
            original, principal=replace(original.principal, tenant_id=str(self.other))
        )
        await self.request(
            "POST", f"/publications/{pub['publication_id']}/catalog-item", body, 404
        )
        self.app.state.test_context = original
        authorization = SimpleNamespace(
            can=AsyncMock(
                side_effect=lambda **kwargs: kwargs["action"] != "catalog.create"
            )
        )
        self.app.dependency_overrides[get_authorization_service] = lambda: authorization
        await self.request(
            "POST", f"/publications/{pub['publication_id']}/catalog-item", body, 403
        )
        self.assertEqual(await self.item_count(), 0)

    async def test_archived_channel_usage_persists_until_explicit_unbind(self) -> None:
        """Архив не разрешает удалить связанный Catalog, но локальный unbind доступен."""
        channel, pub = await self.imported()
        result = await self.request(
            "POST",
            f"/publications/{pub['publication_id']}/catalog-item",
            self.draft(pub),
            201,
        )
        state = await self.request("GET", f"/{channel['channel_id']}")
        await self.request(
            "POST",
            f"/{channel['channel_id']}/archive",
            {"revision": state["revision"]},
            204,
        )
        await self.catalog("DELETE", f"/{result['catalog_item_id']}", status=409)
        page = await self.request(
            "GET",
            f"/connections/{pub['connection_id']}/publications?binding_status=bound",
        )
        bound = page["items"][0]
        await self.request(
            "DELETE",
            f"/publications/{pub['publication_id']}/binding",
            {
                "binding_id": bound["binding_id"],
                "expected_revision": bound["representation_revision"],
            },
            204,
        )
        await self.catalog("DELETE", f"/{result['catalog_item_id']}", status=204)
        await self.request(
            "POST",
            f"/publications/{pub['publication_id']}/catalog-item",
            self.draft(pub),
            409,
        )

    async def test_stock_mismatch_uses_catalog_calculation_without_confirmation(
        self,
    ) -> None:
        """Выбранный учёт вычисляет наличие независимо от внешнего статуса."""
        _, pub = await self.imported()
        async with self.session() as session:
            payload = (
                await session.execute(
                    select(ExternalPublicationModel.payload).where(
                        ExternalPublicationModel.id == UUID(pub["publication_id"])
                    )
                )
            ).scalar_one()
            payload["stock"] = {"quantity": "1", "status": "out_of_stock"}
            await session.execute(
                update(ExternalPublicationModel)
                .where(ExternalPublicationModel.id == UUID(pub["publication_id"]))
                .values(payload=payload)
            )
        body = self.draft(pub)
        body["values"].update(manage_stock=True, quantity="1", stock_status=None)
        result = await self.request(
            "POST", f"/publications/{pub['publication_id']}/catalog-item", body, 201
        )
        item = await self.catalog("GET", f"/{result['catalog_item_id']}?locale=uk")
        self.assertEqual(item["item"]["stock"]["stock_quantity"], 1)
        self.assertEqual(await self.item_count(), 1)
