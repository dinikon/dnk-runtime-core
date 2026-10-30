"""Реальный HTTP и PostgreSQL для создания Catalog без новых таблиц."""

import asyncio
from datetime import UTC, datetime
from dataclasses import replace
from decimal import Decimal
from unittest.mock import patch
from uuid import UUID
from sqlalchemy import select, func, update
import test.test_catalog_bindings_postgres as binding_support
from src.modules.channels.application.external_publication.catalog_details import (
    PublicationDetails,
    PublicationProductDetails,
    PublicationTranslationDetails,
)
from src.modules.channels.infrastructure.persistence.models.external_publication import (
    ExternalPublicationModel as P,
)
from src.modules.channels.infrastructure.persistence.models.connection import (
    ConnectionModel as N,
)
from src.modules.catalog.infrastructure.persistence.models.catalog_item import (
    CatalogItemModel as K,
)
from src.modules.channels.application.catalog_binding.writes import BindingWrites
from src.modules.channels.domain.catalog_binding.error import CatalogBindingError
from src.modules.channels.presentation.external_publication.catalog_creation_depends import (
    get_publication_images,
)
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_connection import (
    bind_tenant_schema,
)


class FakeDetailsPlatform:
    """Возвращает актуальные типизированные детали вместо сохранённых raw снимков."""

    def __init__(self):
        self.calls = 0
        self.hook = None
        self.sku = None
        self.quantity = Decimal(8)
        self.image_urls = ()
        self.regular_price = None
        self.sale_price = None
        self.sale_from = None
        self.sale_to = None

    def get(self, kind):
        return self

    async def get_details(self, *, config, credentials, publications):
        self.calls += 1
        assert b"test" in credentials
        if self.hook:
            await self.hook()
        root = next(p for p in publications if p.parent_id is None)
        result = []
        for source in sorted(
            publications, key=lambda p: (p.parent_id is not None, p.external_id)
        ):
            variable = source.kind == "variable"
            result.append(
                PublicationProductDetails(
                    source.resource_type,
                    source.external_id,
                    root.external_id if source.parent_id else None,
                    source.kind,
                    self.sku or "S-" + str(source.id),
                    (
                        PublicationTranslationDetails(
                            "uk",
                            "Актуальний товар",
                            "<p>Повний опис</p><script>bad()</script>",
                        ),
                    ),
                    self.image_urls,
                    True if not source.parent_id else False,
                    self.quantity if not source.parent_id else None,
                    None if not source.parent_id else "out_of_stock",
                    "notify" if not source.parent_id else "no",
                    regular_price=self.regular_price if not variable else None,
                    currency=(
                        "UAH"
                        if self.regular_price is not None and not variable
                        else None
                    ),
                    sale_price=self.sale_price if not variable else None,
                    date_on_sale_from=self.sale_from if not variable else None,
                    date_on_sale_to=self.sale_to if not variable else None,
                )
            )
        return PublicationDetails(tuple(result))


class FailedImages:
    async def download(self, identifier, url):
        return None, "Изображение пропущено: источник недоступен."


class PublicationCatalogPostgresTests(binding_support.CatalogBindingsPostgresTests):
    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.platform = FakeDetailsPlatform()
        for target, value in [
            ("get_platforms", self.platform),
            ("get_cipher", self.cipher),
        ]:
            p = patch(
                "src.modules.channels.presentation.external_publication.catalog_creation_depends."
                + target,
                return_value=value,
            )
            p.start()
            self.addCleanup(p.stop)
        self.app.dependency_overrides[get_publication_images] = lambda: FailedImages()

    async def count_catalog(self):
        async with self.sessions() as session:
            await bind_tenant_schema(
                await session.connection(), self.tenant, self.naming
            )
            return await session.scalar(select(func.count()).select_from(K))

    async def create_from(self, channel, pub, status=201):
        return await self.call(
            "POST",
            f"/channels/{channel}/publications/{pub}/catalog-item",
            status=status,
        )

    async def test_creation_shapes_and_repeat_return_same_product(self):
        for platform, variable in [
            ("prom", False),
            ("prom", True),
            ("woocommerce", False),
            ("woocommerce", True),
            ("rozetka", False),
        ]:
            channel, pubs = await self.source(platform, variable=variable)
            before = await self.count_catalog()
            result = await self.create_from(channel, pubs[0])
            root = result["catalog_item_id"]
            details = (await self.call("GET", f"/catalog/items/{root}?locale=uk"))[
                "item"
            ]
            self.assertEqual(details["kind"], "variable" if variable else "simple")
            self.assertEqual(details["status"], "draft")
            self.assertIsNone(details["price_specification"])
            self.assertEqual(details["content"]["title"], "Актуальний товар")
            self.assertNotIn("<script>", details["content"]["body"])
            if not variable or platform == "woocommerce":
                self.assertEqual(
                    details["stock"],
                    {
                        "manage_stock": True,
                        "stock_quantity": 8,
                        "stock_status": None,
                        "backorders": "notify",
                    },
                )
            if variable and platform == "woocommerce":
                children = (
                    await self.call("GET", f"/catalog/items/{root}/variants?locale=uk")
                )["items"]
                child = (
                    await self.call(
                        "GET",
                        f"/catalog/items/{root}/variants/{children[0]['id']}?locale=uk",
                    )
                )["item"]
                self.assertFalse(child["stock"]["manage_stock"])
                self.assertEqual(child["stock"]["stock_status"], "out_of_stock")
                self.assertEqual(child["stock_source"], "parent")
                self.assertEqual(child["effective_stock"], details["stock"])
            group = (
                await self.call(
                    "GET",
                    f"/channels/{channel}/catalog-bindings/{result['binding_group_id']}?locale=uk",
                )
            )["binding"]
            self.assertEqual(group["preview"]["assessment"]["state"], "linked")
            count = 2 if variable and platform == "prom" else 1
            self.assertEqual(len(group["group"]["items"]), count)
            self.assertEqual(
                await self.count_catalog(), before + count + (1 if variable else 0)
            )
            again = await self.create_from(channel, pubs[-1], 200)
            self.assertFalse(again["created"])
            self.assertEqual(again["catalog_item_id"], root)
            self.assertEqual(self.platform.calls, 1)
            self.platform.calls = 0

    async def test_sku_conflicts_and_failed_photos_create_with_warnings(self):
        existing = await self.call("POST", "/catalog/items", {"sku": "TAKEN"}, 201)
        self.platform.sku = "TAKEN"
        self.platform.image_urls = ("https://img.example/image.png",)
        channel, pubs = await self.source("prom", variable=True)
        result = await self.create_from(channel, pubs[0])
        self.assertEqual(len(result["warnings"]), 2)
        root = result["catalog_item_id"]
        variants = await self.call("GET", f"/catalog/items/{root}/variants?locale=uk")
        self.assertTrue(all(v["sku"] is None for v in variants["items"]))
        self.assertEqual(
            (await self.call("GET", f"/catalog/items/{existing['id']}?locale=uk"))[
                "item"
            ]["sku"],
            "TAKEN",
        )

    async def test_rozetka_stale_old_price_creates_catalog_at_the_current_price(self):
        from test.test_publication_catalog_creation import DetailsHttp
        from src.modules.channels.infrastructure.registry import InstalledPlatforms

        channel, pubs = await self.source("rozetka")
        async with self.sessions() as session:
            await bind_tenant_schema(
                await session.connection(), self.tenant, self.naming
            )
            await session.execute(
                update(P)
                .where(P.id == UUID(pubs[0]))
                .values(
                    external_id="3:offer",
                    resource_type="source_offer",
                    platform_data={"item_id": 42, "sync_source_id": 3},
                )
            )
            await session.commit()
        http = DetailsHttp(
            {
                "/goods/details?": {
                    "success": True,
                    "content": {
                        "item": [
                            {
                                "sync_source_id": 3,
                                "price_offer_id": "offer",
                                "item_id": 42,
                                "name_ua": "Назва",
                                "name_ru": "Название",
                                "description_ua": "Опис",
                                "description": "Описание",
                                "price": 369,
                                "price_old": 350,
                                "price_promo": 369,
                                "stock_quantity": 14,
                                "photo_preview": "https://img.example/thumb.png",
                            }
                        ]
                    },
                }
            }
        )
        with patch(
            "src.modules.channels.presentation.external_publication.catalog_creation_depends.get_platforms",
            return_value=InstalledPlatforms(http),
        ):
            result = await self.create_from(channel, pubs[0])
        details = (
            await self.call(
                "GET", f"/catalog/items/{result['catalog_item_id']}?locale=uk"
            )
        )["item"]
        self.assertEqual(
            Decimal(details["price_specification"]["regular_price"]), Decimal(369)
        )
        self.assertIsNone(details["price_specification"]["sale_price"])
        self.assertEqual(details["stock"]["stock_quantity"], 14)
        self.assertTrue(any("Старая цена" in warning for warning in result["warnings"]))
        group = (
            await self.call(
                "GET",
                f"/channels/{channel}/catalog-bindings/{result['binding_group_id']}?locale=uk",
            )
        )["binding"]
        self.assertEqual(group["preview"]["assessment"]["state"], "linked")

    async def test_prices_are_saved_for_simple_and_each_sellable_variant(self):
        self.platform.regular_price = Decimal("100.123456")
        self.platform.sale_price = Decimal("90.123456")
        self.platform.sale_from = datetime(2030, 1, 1, tzinfo=UTC)
        self.platform.sale_to = datetime(2030, 2, 1, tzinfo=UTC)
        for platform, variable in (
            ("rozetka", False),
            ("woocommerce", False),
            ("woocommerce", True),
            ("prom", False),
            ("prom", True),
        ):
            channel, pubs = await self.source(platform, variable=variable)
            result = await self.create_from(channel, pubs[0])
            root = result["catalog_item_id"]
            if variable:
                container = (
                    await self.call("GET", f"/catalog/items/{root}?locale=uk")
                )["item"]
                self.assertIsNone(container["price_specification"])
                children = (
                    await self.call("GET", f"/catalog/items/{root}/variants?locale=uk")
                )["items"]
                items = [
                    (
                        await self.call(
                            "GET",
                            f"/catalog/items/{root}/variants/{child['id']}?locale=uk",
                        )
                    )["item"]
                    for child in children
                ]
            else:
                items = [
                    (await self.call("GET", f"/catalog/items/{root}?locale=uk"))["item"]
                ]
            for item in items:
                price = item["price_specification"]
                self.assertEqual(
                    Decimal(price["regular_price"]), self.platform.regular_price
                )
                self.assertEqual(Decimal(price["sale_price"]), self.platform.sale_price)
                self.assertEqual(price["currency"], "UAH")
                self.assertEqual(
                    datetime.fromisoformat(
                        price["date_on_sale_from"].replace("Z", "+00:00")
                    ),
                    self.platform.sale_from,
                )
                self.assertEqual(
                    datetime.fromisoformat(
                        price["date_on_sale_to"].replace("Z", "+00:00")
                    ),
                    self.platform.sale_to,
                )

    async def test_config_change_and_binding_failure_leave_no_catalog(self):
        channel, pubs = await self.source("woocommerce")
        before = await self.count_catalog()

        async def change_revision():
            await self.call(
                "PATCH",
                f"/channels/{channel}",
                {
                    "expected_revision": 1,
                    "credentials": {
                        "consumer_key": "changed",
                        "consumer_secret": "changed",
                    },
                },
            )

        self.platform.hook = change_revision
        await self.create_from(channel, pubs[0], 409)
        self.assertEqual(await self.count_catalog(), before)
        self.platform.hook = None
        channel, pubs = await self.source("prom")
        with patch.object(
            BindingWrites,
            "create",
            side_effect=CatalogBindingError(
                "binding_publication_occupied", conflict=True
            ),
        ):
            await self.create_from(channel, pubs[0], 409)
        self.assertEqual(await self.count_catalog(), before)

    async def test_concurrent_requests_and_fractional_quantity(self):
        channel, pubs = await self.source("rozetka")
        barrier = asyncio.Barrier(2)
        self.platform.hook = barrier.wait
        path = f"/api/console/channels/{channel}/publications/{pubs[0]}/catalog-item"
        results = await asyncio.gather(
            *(self.client.post(path, headers=self.headers) for _ in range(2))
        )
        self.assertEqual(
            sorted(r.status_code for r in results),
            [200, 201],
            str([r.text for r in results]),
        )
        self.assertEqual(len({r.json()["catalog_item_id"] for r in results}), 1)
        self.platform.hook = None
        self.platform.quantity = Decimal("1.5")
        channel, pubs = await self.source("woocommerce")
        before = await self.count_catalog()
        await self.create_from(channel, pubs[0], 422)
        self.assertEqual(await self.count_catalog(), before)

    async def test_sku_race_retries_entire_family_after_rollback(self):
        from src.modules.catalog.infrastructure.catalog_item.sku import (
            SqlAlchemyCatalogItemSku,
        )

        channel, pubs = await self.source("woocommerce", variable=True)
        sku = "S-" + pubs[1]
        await self.call("POST", "/catalog/items", {"sku": sku}, 201)
        original = SqlAlchemyCatalogItemSku.in_use
        calls = 0

        async def miss_first_two(repository, value):
            nonlocal calls
            if value == sku:
                calls += 1
                if calls <= 2:
                    return False
            return await original(repository, value)

        before = await self.count_catalog()
        with patch.object(SqlAlchemyCatalogItemSku, "in_use", new=miss_first_two):
            result = await self.create_from(channel, pubs[0])
        self.assertTrue(result["warnings"])
        self.assertEqual(await self.count_catalog(), before + 2)

    async def test_successful_images_are_attached_to_both_locales(self):
        from uuid import uuid4
        from datetime import datetime, UTC
        from src.modules.files.infrastructure.assembly import (
            build_artifact_files_facade,
        )

        file_id = uuid4()
        async with self.sessions() as session:
            await bind_tenant_schema(
                await session.connection(), self.tenant, self.naming
            )
            from sqlalchemy import insert
            from src.modules.files.infrastructure.persistence.models.storage_provider import (
                StorageProviderModel,
            )
            from src.modules.files.infrastructure.persistence.models.bucket import (
                BucketModel,
            )

            provider, bucket = uuid4(), uuid4()
            await session.execute(
                insert(StorageProviderModel).values(
                    id=provider,
                    name="test",
                    kind="minio",
                    is_system=True,
                    config_ref="system_minio",
                )
            )
            await session.execute(
                insert(BucketModel).values(
                    id=bucket,
                    provider_id=provider,
                    name=f"dnk-tenant-{self.tenant.hex}",
                    status="ready",
                )
            )
            facade = build_artifact_files_facade(session)
            await facade.reserve(
                self.tenant, file_id, "test.png", "image/png", 4, datetime.now(UTC)
            )
            await facade.confirm(file_id, 4)
            await session.commit()

        class ReadyImage:
            async def download(self, identifier, url):
                return file_id, None

        self.app.dependency_overrides[get_publication_images] = lambda: ReadyImage()
        self.platform.image_urls = ("https://img.example/image.png",)
        original = self.platform.get_details

        async def bilingual_details(**kwargs):
            details = await original(**kwargs)
            return replace(
                details,
                products=tuple(
                    replace(
                        product,
                        translations=(
                            *product.translations,
                            PublicationTranslationDetails(
                                "ru", "Русское название", "<p>Русское описание</p>"
                            ),
                        ),
                    )
                    for product in details.products
                ),
            )

        self.platform.get_details = bilingual_details
        channel, pubs = await self.source("rozetka")
        result = await self.create_from(channel, pubs[0])
        details = (
            await self.call(
                "GET", f"/catalog/items/{result['catalog_item_id']}?locale=uk"
            )
        )["item"]
        self.assertEqual(details["gallery"]["images"][0]["file_id"], str(file_id))
        russian = (
            await self.call(
                "GET", f"/catalog/items/{result['catalog_item_id']}?locale=ru"
            )
        )["item"]
        self.assertEqual(russian["content"]["title"], "Русское название")
        self.assertEqual(russian["content"]["body"], "<p>Русское описание</p>")
        self.assertEqual(russian["gallery"]["images"][0]["file_id"], str(file_id))
        self.assertNotEqual(
            details["gallery"]["images"][0]["id"],
            russian["gallery"]["images"][0]["id"],
        )
        self.assertFalse(result["warnings"])

    async def test_platform_api_and_media_are_outside_request_transaction(self):
        from src.modules.channels.infrastructure.external_publication.catalog_creation.query_repository import (
            SqlAlchemyPublicationCreationRead,
        )

        original = SqlAlchemyPublicationCreationRead.snapshot
        sessions = []

        async def observe(repository, channel_id, publication_id):
            result = await original(repository, channel_id, publication_id)
            sessions.append(repository.session)
            return result

        async def check():
            self.assertFalse(sessions[-1].in_transaction())

        class CheckingImages:
            async def download(inner, identifier, url):
                await check()
                return None, "Изображение пропущено."

        self.platform.hook = check
        self.platform.image_urls = ("https://img.example/test.png",)
        self.app.dependency_overrides[get_publication_images] = lambda: CheckingImages()
        channel, pubs = await self.source("prom")
        with patch.object(SqlAlchemyPublicationCreationRead, "snapshot", new=observe):
            await self.create_from(channel, pubs[0])
