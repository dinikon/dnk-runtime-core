"""Сохранённый ассортимент Feed через реальные Catalog, API и PostgreSQL."""

import asyncio
import os
import unittest
from unittest.mock import patch, Mock, AsyncMock
from uuid import UUID, uuid4
from sqlalchemy import select, func, update, delete, text
from sqlalchemy.exc import IntegrityError
from test import test_feed_builder_calculation_postgres as fixture
from src.modules.feed_builder.presentation.publication.router import router
from src.modules.feed_builder.infrastructure.persistence.models.publication import (
    FeedPublicationModel,
)
from src.modules.feed_builder.domain.publication.aggregate import FeedPublication
from src.modules.feed_builder.domain.feed.aggregate import Feed
from src.modules.catalog.infrastructure.persistence.models.catalog_item import (
    CatalogItemModel,
)
from src.modules.identity.domain.auth.principal import Principal
from src.modules.identity.domain.auth.request_context import RequestContext
from src.modules.feed_builder.presentation.publication.depends import (
    get_publication_catalog,
)
from src.modules.feed_builder.application.publication.port.catalog_subjects import (
    PublicationSourceUnavailableError,
)


@unittest.skipUnless(
    os.environ.get("TEST_POSTGRES_URL"), "Requires disposable PostgreSQL"
)
class FeedPublicationsPostgresTests(unittest.IsolatedAsyncioTestCase):
    """Проверяет атомарность, идентичность, статусы и tenant-изоляцию состава."""

    refresh_csrf = fixture.FeedCalculationPostgresTests.refresh_csrf
    scoped_session = fixture.FeedCalculationPostgresTests.scoped_session
    create = fixture.FeedCalculationPostgresTests.create
    item = fixture.FeedCalculationPostgresTests.item
    asyncTearDown = fixture.FeedCalculationPostgresTests.asyncTearDown

    async def asyncSetUp(self) -> None:
        """Собирает действующие владельческие API на изолированной тестовой базе."""
        await fixture.FeedCalculationPostgresTests.asyncSetUp(self)
        self.app.include_router(router, prefix="/api/console")
        self.path = f"{self.base}/{self.feed['id']}/publications"

    async def add(
        self,
        references: list[dict[str, str | None]],
        *,
        expected: int = 1,
        status: int = 200,
    ) -> dict:
        """Отправляет явный пакет с настоящими CSRF и auth зависимостями."""
        response = await self.client.post(
            self.path,
            headers=self.headers,
            json={"expected_feed_version": expected, "item_references": references},
        )
        self.assertEqual(response.status_code, status, response.text)
        return response.json()

    async def status(
        self, identifier: str, version: int, status: str, expected: int = 200
    ) -> dict:
        """Изменяет участие через защищённую версией команду."""
        response = await self.client.patch(
            f"/api/console/feed-builder/publications/{identifier}/status",
            headers=self.headers,
            json={"expected_version": version, "status": status},
        )
        self.assertEqual(response.status_code, expected, response.text)
        return response.json()

    async def test_migration_preserves_publication_dates_and_sets_insert_defaults(
        self,
    ) -> None:
        """Проверяет сохранность доменных дат и вставку без дат после обновления схемы."""
        item_id = await self.item()
        result = await self.add([{"catalog_item_id": item_id}])
        identifier = UUID(result["items"][0]["id"])
        schema = self.schemas[0]
        table = f'"{schema}".fb_publications'
        read_dates = text(f"SELECT created_at, updated_at FROM {table} WHERE id=:id")
        async with self.engine.begin() as connection:
            dates = (await connection.execute(read_dates, {"id": identifier})).one()
            await self.migrator.downgrade(connection, schema, "0023_catalog_categories")
            await self.migrator.upgrade(connection, schema)
            self.assertEqual(
                (await connection.execute(read_dates, {"id": identifier})).one(), dates
            )
            inserted = (
                await connection.execute(
                    text(
                        f"INSERT INTO {table} (id, feed_id, catalog_item_id, status, row_version, overrides) "
                        "VALUES (:id, :feed, :item, 'DRAFT', 1, '{}') RETURNING created_at, updated_at"
                    ),
                    {"id": uuid4(), "feed": UUID(self.feed["id"]), "item": uuid4()},
                )
            ).one()
            now = await connection.scalar(select(func.current_timestamp()))
            self.assertEqual(tuple(inserted), (now, now))

    async def test_add_repeat_pause_archive_restore_keeps_identity_and_overrides(
        self,
    ) -> None:
        """Повтор не стирает состояние, архив сохраняет ID и точные ручные значения."""
        item = await self.item()
        root = await self.item("variable")
        child = await self.item("variant", parent=root)
        refs = [
            {"catalog_item_id": item, "catalog_variant_id": None},
            {"catalog_item_id": root, "catalog_variant_id": child},
        ]
        added = await self.add(refs + refs)
        self.assertEqual(len(added["items"]), 2)
        self.assertTrue(all(p["outcome"] == "CREATED" for p in added["items"]))
        identifier = added["items"][1]["id"]
        field = str(uuid4())
        overrides = {
            field: {"mode": "MANUAL", "value": {"amount": "123.4567890123456789"}},
            str(uuid4()): {"mode": "MANUAL", "value": None},
        }
        async with self.scoped_session() as session:
            await session.execute(
                update(FeedPublicationModel)
                .where(FeedPublicationModel.id == UUID(identifier))
                .values(overrides=overrides, updated_at=self.app.state.clock.now())
            )
        changed = await self.status(identifier, 1, "PAUSED")
        self.assertEqual(changed["version"], 2)
        await self.status(identifier, 1, "ENABLED", 409)
        repeated = await self.add(refs)
        self.assertEqual(repeated["items"][1]["id"], identifier)
        self.assertEqual(repeated["items"][1]["status"], "PAUSED")
        response = await self.client.delete(
            f"/api/console/feed-builder/publications/{identifier}?expected_version=2",
            headers=self.headers,
        )
        self.assertEqual(response.status_code, 204, response.text)
        self.assertEqual((await self.add(refs))["items"][1]["status"], "ARCHIVED")
        self.assertEqual((await self.client.get(self.path)).json()["total"], 1)
        archived = (await self.client.get(self.path + "?status=ARCHIVED")).json()
        self.assertEqual(archived["items"][0]["id"], identifier)
        response = await self.client.post(
            f"/api/console/feed-builder/publications/{identifier}/restore",
            headers=self.headers,
            json={"expected_version": 3},
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["version"], 4)
        self.app.dependency_overrides[get_publication_catalog] = lambda: Mock(
            read_many=AsyncMock(
                side_effect=PublicationSourceUnavailableError("offline")
            )
        )
        noop_restore = await self.client.post(
            f"/api/console/feed-builder/publications/{identifier}/restore",
            headers=self.headers,
            json={"expected_version": 4},
        )
        self.assertEqual(noop_restore.status_code, 200, noop_restore.text)
        self.assertEqual(noop_restore.json()["version"], 4)
        self.app.dependency_overrides.pop(get_publication_catalog)
        noop = await self.status(identifier, 4, "ENABLED")
        self.assertEqual(noop["version"], 4)
        async with self.scoped_session() as session:
            row = (
                await session.execute(
                    select(FeedPublicationModel.overrides).where(
                        FeedPublicationModel.id == UUID(identifier)
                    )
                )
            ).scalar_one()
            self.assertEqual(row, overrides)
        self.assertEqual(
            (await self.client.get(f"{self.base}/{self.feed['id']}")).json()["version"],
            1,
        )

    async def test_atomic_validation_concurrent_add_and_fixed_variant_selection(
        self,
    ) -> None:
        """Неверная пара откатывает пакет; перекрывающиеся запросы не создают дубль."""
        simple = await self.item()
        root = await self.item("variable")
        white = await self.item("variant", parent=root)
        await self.add(
            [{"catalog_item_id": simple}, {"catalog_item_id": root}], status=404
        )
        self.assertEqual((await self.client.get(self.path)).json()["total"], 0)
        other = await self.item("variable")
        await self.add(
            [{"catalog_item_id": other, "catalog_variant_id": white}], status=404
        )
        endpoint = f"/api/console/feed-builder/feeds/{self.feed['id']}/variant-selection/{root}"
        snapshot = (await self.client.get(endpoint)).json()
        self.assertEqual(len(snapshot["items"]), 1)
        await self.item("variant", parent=root)
        ref = {"catalog_item_id": root, "catalog_variant_id": white}
        first, second = await asyncio.gather(self.add([ref]), self.add([ref]))
        self.assertEqual(first["items"][0]["id"], second["items"][0]["id"])
        self.assertEqual(
            {first["items"][0]["outcome"], second["items"][0]["outcome"]},
            {"CREATED", "EXISTING"},
        )
        fixed = [
            {
                "catalog_item_id": s["catalog_item_id"],
                "catalog_variant_id": s["catalog_variant_id"],
            }
            for s in snapshot["items"]
        ]
        await self.add(fixed)
        self.assertEqual((await self.client.get(self.path)).json()["total"], 1)
        await self.add([{"catalog_item_id": simple}] * 101, status=422)
        await self.add([{"catalog_item_id": simple}], expected=2, status=409)

    async def test_page_search_details_missing_sources_and_read_side(self) -> None:
        """Пагинация и поиск выполняются на сервере; удалённая позиция не удаляет участие."""
        items = [await self.item() for _ in range(3)]
        added = await self.add([{"catalog_item_id": i} for i in items])
        with (
            patch.object(Feed, "restore", side_effect=AssertionError("read side")),
            patch.object(
                FeedPublication, "restore", side_effect=AssertionError("read side")
            ),
        ):
            page = await self.client.get(self.path + "?limit=2&offset=0")
            self.assertEqual(page.status_code, 200, page.text)
            data = page.json()
            self.assertEqual(data["total"], 3)
            self.assertEqual(len(data["items"]), 2)
            card = await self.client.get(
                "/api/console/feed-builder/publications/" + added["items"][0]["id"]
            )
            self.assertEqual(card.status_code, 200, card.text)
        await fixture.crud_support.FeedCrudPostgresTests.seed_schema_locales(self)
        renamed = await self.client.patch(
            f"{self.catalog}/{items[0]}?locale=uk",
            headers=self.headers,
            json={
                "content": {
                    "expected_schema_version": 1,
                    "values": {"title": "Новое название позиции"},
                }
            },
        )
        self.assertEqual(renamed.status_code, 200, renamed.text)
        by_title = await self.client.get(
            self.path, params={"search": "Новое название", "locale": "uk"}
        )
        self.assertEqual(by_title.status_code, 200, by_title.text)
        self.assertEqual(by_title.json()["total"], 1)
        self.assertEqual(by_title.json()["items"][0]["title"], "Новое название позиции")
        self.assertEqual(
            (await self.client.get(self.path, params={"search": "%"})).json()["total"],
            0,
        )
        sku = card.json()["publication"]["sku"]
        found = await self.client.get(self.path, params={"search": sku})
        self.assertEqual(found.status_code, 200, found.text)
        self.assertEqual(found.json()["total"], 1)
        self.assertEqual(
            (await self.client.get(self.path, params={"search": "NO_MATCH"})).json()[
                "total"
            ],
            0,
        )
        async with self.scoped_session() as session:
            await session.execute(
                delete(CatalogItemModel).where(CatalogItemModel.id == UUID(items[0]))
            )
        card = (
            await self.client.get(
                "/api/console/feed-builder/publications/" + added["items"][0]["id"]
            )
        ).json()
        self.assertFalse(card["publication"]["source_available"])
        self.assertEqual((await self.client.get(self.path)).json()["total"], 3)

    async def test_permissions_tenant_csrf_dependency_and_feed_archive(self) -> None:
        """Защищает состав правами и Feed-блокировкой, различая технический сбой."""
        item = await self.item()
        body = {
            "expected_feed_version": 1,
            "item_references": [{"catalog_item_id": item}],
        }
        self.assertEqual(
            (await self.client.post(self.path, json=body)).status_code, 403
        )

        class Denied:
            """Запрещает чтение Catalog независимо от Feed."""

            async def can(self, **kwargs: object) -> bool:
                """Отделяет права источника от управления ассортиментом."""
                return kwargs["action"] != "catalog.item.read"

        self.app.state.authorization_service = Denied()
        await self.add(body["item_references"], status=403)
        del self.app.state.authorization_service
        self.app.dependency_overrides[get_publication_catalog] = lambda: Mock(
            read_many=AsyncMock(
                side_effect=PublicationSourceUnavailableError("offline")
            )
        )
        await self.add(body["item_references"], status=503)
        self.app.dependency_overrides.pop(get_publication_catalog)
        added = await self.add(body["item_references"])
        identifier = added["items"][0]["id"]
        original = self.app.state.test_context
        self.app.state.test_context = RequestContext(
            Principal(str(self.actor), str(self.other.uuid), "feed-test", ("member",)),
            None,
            None,
            None,
        )
        await self.refresh_csrf()
        await self.add(body["item_references"], status=404)
        self.assertEqual(
            (
                await self.client.get(
                    "/api/console/feed-builder/publications/" + identifier
                )
            ).status_code,
            404,
        )
        self.app.state.test_context = original
        await self.refresh_csrf()
        await self.client.delete(
            f"{self.base}/{self.feed['id']}?expected_version=1", headers=self.headers
        )
        await self.add(body["item_references"], expected=2, status=409)
        await self.status(identifier, 1, "PAUSED", 409)
        response = await self.client.get(self.path)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["feed_status"], "ARCHIVED")

    async def test_storage_uniqueness_commit_rollback_and_bounded_selection(
        self,
    ) -> None:
        """Проверяет NULL-идентичность, сбой commit и полное отклонение большого семейства."""
        from sqlalchemy import insert
        from src.modules.shared.infrastructure.persistence.unit_of_work.sqlalchemy import (
            UnitOfWork,
        )

        simple = await self.item()
        with patch.object(
            UnitOfWork, "commit", side_effect=RuntimeError("test commit failure")
        ):
            with self.assertRaises(RuntimeError):
                await self.add([{"catalog_item_id": simple}])
        self.assertEqual((await self.client.get(self.path)).json()["total"], 0)
        result = await self.add([{"catalog_item_id": simple}])
        async with self.scoped_session() as session:
            original = dict(
                (
                    await session.execute(
                        select(FeedPublicationModel.__table__).where(
                            FeedPublicationModel.id == UUID(result["items"][0]["id"])
                        )
                    )
                )
                .mappings()
                .one()
            )
        with self.assertRaises(IntegrityError):
            async with self.scoped_session() as session:
                await session.execute(
                    insert(FeedPublicationModel).values(**(original | {"id": uuid4()}))
                )
        root = await self.item("variable")
        child = await self.item("variant", parent=root)
        async with self.scoped_session() as session:
            seed = dict(
                (
                    await session.execute(
                        select(CatalogItemModel.__table__).where(
                            CatalogItemModel.id == UUID(child)
                        )
                    )
                )
                .mappings()
                .one()
            )
            seed.pop("required_parent_kind")
            await session.execute(
                insert(CatalogItemModel),
                [
                    seed | {"id": uuid4(), "sku": f"OVERFLOW-{uuid4().hex}"}
                    for _ in range(100)
                ],
            )
        endpoint = f"/api/console/feed-builder/feeds/{self.feed['id']}/variant-selection/{root}"
        selection = await self.client.get(endpoint)
        self.assertEqual(selection.status_code, 422, selection.text)
        self.assertEqual((await self.client.get(self.path)).json()["total"], 1)
        missing = await self.client.get(
            f"/api/console/feed-builder/feeds/{self.feed['id']}/variant-selection/{uuid4()}"
        )
        self.assertEqual(missing.status_code, 404, missing.text)
