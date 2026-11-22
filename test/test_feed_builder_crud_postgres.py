"""Полная вертикаль Feed CRUD на изолированных PostgreSQL tenant-схемах."""

import asyncio
import copy
import os
from contextlib import asynccontextmanager
from dataclasses import replace
from unittest.mock import patch
from uuid import uuid4
import unittest
from collections.abc import AsyncIterator

from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import NullPool
from sqlalchemy.schema import CreateSchema, DropSchema

from src.config import dnk_config
from src.modules.identity.domain.auth.principal import Principal
from src.modules.identity.domain.auth.request_context import RequestContext
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.shared.infrastructure.persistence.global_migrations import (
    GlobalMigrator,
)
from src.modules.shared.infrastructure.persistence.unit_of_work.sqlalchemy import (
    UnitOfWork,
)
from src.modules.tenancy.application.tenant.tenant_schema_naming import (
    TenantSchemaNaming,
)
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_migrations import (
    TenantMigrator,
)
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_connection import (
    bind_tenant_schema,
)
from src.modules.feed_builder.domain.feed.aggregate import Feed
from src.modules.feed_builder.domain.feed.value_object.feed_id import FeedIdVO
from src.modules.feed_builder.domain.feed.value_object.feed_name import FeedNameVO
from src.modules.feed_builder.domain.feed.value_object.feed_version import FeedVersionVO
from src.modules.feed_builder.domain.feed.error import (
    FeedVersionConflictError,
    FeedCodeConflictError,
)
from src.modules.feed_builder.infrastructure.persistence.models.feed import FeedModel
from src.modules.feed_builder.infrastructure.feed.persistence.repository import (
    SqlAlchemyFeedRepository,
)
from src.modules.feed_builder.infrastructure.feed.persistence.query_repository import (
    SqlAlchemyFeedQueryRepository,
)
from src.modules.feed_builder.presentation.feed.router import router, metadata_router
from test.crm_company_support import company_app
from test.test_feed_builder_crud import rich_feed, NOW

URL = os.environ.get("TEST_POSTGRES_URL")


class DenyFeedAccess:
    """Запрещает операции через существующий порт авторизации."""

    async def can(self, **kwargs: object) -> bool:
        """Отклоняет запрос до выполнения сценария."""
        return False


@unittest.skipUnless(URL, "TEST_POSTGRES_URL requires a disposable PostgreSQL database")
class FeedCrudPostgresTests(unittest.IsolatedAsyncioTestCase):
    """Проверяет миграции, SQL, API, версии и tenant-изоляцию с реальным UoW."""

    async def asyncSetUp(self) -> None:
        """Создаёт два tenant, мигрирует их и подключает настоящие auth/CSRF зависимости."""
        self.engine = create_async_engine(URL, poolclass=NullPool)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        self.naming = TenantSchemaNaming(dnk_config.SCHEMA_PREFIX)
        self.tenant = EntityIdVO(uuid4())
        self.other = EntityIdVO(uuid4())
        self.actor = uuid4()
        self.schemas = [
            self.naming.schema_name(value) for value in (self.tenant, self.other)
        ]
        self.migrator = TenantMigrator()
        async with self.engine.begin() as connection:
            await GlobalMigrator().upgrade(connection)
            for schema in self.schemas:
                await connection.execute(CreateSchema(schema))
                await self.migrator.upgrade(connection, schema)
        self.context = RequestContext(
            Principal(str(self.actor), str(self.tenant.uuid), "feed-test", ("member",)),
            None,
            None,
            None,
        )
        self.app = company_app(self.sessions, self.context, scoped_connection=True)
        self.app.include_router(router, prefix="/api/console")
        self.app.include_router(metadata_router, prefix="/api/console")
        self.origin = (
            "http" if dnk_config.AUTH.allow_insecure_http else "https"
        ) + "://tenant.example"
        self.client = AsyncClient(
            transport=ASGITransport(app=self.app, raise_app_exceptions=True),
            base_url=self.origin,
        )
        await self.refresh_csrf()
        self.base = "/api/console/feed-builder/feeds"

    async def refresh_csrf(self) -> None:
        """Получает настоящий CSRF token для текущего контекста."""
        token = (await self.client.get("/csrf")).json()["csrf_token"]
        self.headers = {"Origin": self.origin, "X-CSRF-Token": token}

    async def asyncTearDown(self) -> None:
        """Удаляет только тестовые tenant-схемы и закрывает соединения."""
        await self.client.aclose()
        async with self.engine.begin() as connection:
            for schema in self.schemas:
                await connection.execute(
                    DropSchema(schema, cascade=True, if_exists=True)
                )
        await self.engine.dispose()

    @asynccontextmanager
    async def scoped_session(
        self, tenant: EntityIdVO | None = None
    ) -> AsyncIterator[AsyncSession]:
        """Открывает реальный внешний UoW с доверенной tenant-привязкой."""
        async with self.engine.connect() as connection:
            await bind_tenant_schema(
                connection, (tenant or self.tenant).uuid, self.naming
            )
            async with UnitOfWork(
                async_sessionmaker(connection, expire_on_commit=False)
            ) as uow:
                yield uow.session

    async def create(
        self, code: str = "partner-feed", *, xml: bool = False
    ) -> dict[str, object]:
        """Создаёт Feed через HTTP и проверяет начальные значения."""
        settings = (
            {
                "format": "xml",
                "root_name": "offers",
                "item_name": "offer",
                "encoding": "utf-8",
            }
            if xml
            else {
                "format": "csv",
                "delimiter": ";",
                "encoding": "utf-8",
                "include_header": False,
            }
        )
        response = await self.client.post(
            self.base,
            headers=self.headers,
            json={
                "name": "Партнёрский фид",
                "code": code,
                "export_settings": {"format_settings": settings},
            },
        )
        self.assertEqual(response.status_code, 201, response.text)
        data = response.json()
        self.assertEqual(data["status"], "DRAFT")
        self.assertEqual(data["version"], 1)
        self.assertEqual(data["schema"]["root"]["fields"], [])
        self.assertEqual(data["export_settings"]["format_settings"], settings)
        return data

    async def seed_schema_locales(self) -> None:
        """Подготавливает только локали временной тестовой БД для owner-порта."""
        async with self.engine.begin() as connection:
            await connection.execute(
                text(
                    "INSERT INTO public.ref_locales (code,language_code,name,active) VALUES ('uk','uk','Українська',true),('ru','ru','Русский',true) ON CONFLICT (code) DO UPDATE SET active=true"
                )
            )

    async def test_schema_full_workflow_metadata_reorder_empty_and_archive(
        self,
    ) -> None:
        """Проходит рабочий сценарий схемы с настоящими auth, CSRF, SQL и UoW."""
        from test.test_feed_builder_schema import source_schema_document

        await self.seed_schema_locales()
        created = await self.create()
        path = self.base + "/" + created["id"]
        for endpoint, count in [
            ("field-types", 3),
            ("source-paths", 4),
            ("transforms", 3),
        ]:
            response = await self.client.get("/api/console/feed-builder/" + endpoint)
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(len(response.json()["items"]), count)
        definition = source_schema_document()
        saved = await self.client.put(
            path + "/schema/draft",
            headers=self.headers,
            json={"expected_version": 1, "definition": definition},
        )
        self.assertEqual(saved.status_code, 200, saved.text)
        self.assertEqual(saved.json()["definition"], definition)
        self.assertEqual(saved.json()["version"], 2)
        self.assertEqual(
            (await self.client.get(path + "/schema")).json(),
            {
                "feed_id": created["id"],
                "version": 2,
                "status": "DRAFT",
                "definition": definition,
            },
        )
        self.assertEqual(
            (await self.client.get(self.base)).json()["items"][0]["fields_count"], 4
        )
        noop = await self.client.put(
            path + "/schema/draft",
            headers=self.headers,
            json={"expected_version": 2, "definition": definition},
        )
        self.assertEqual(noop.json()["version"], 2)
        fields = definition["root"]["fields"]
        fields.reverse()
        fields[0]["label"] = "Цена партнёра"
        changed = await self.client.put(
            path + "/schema/draft",
            headers=self.headers,
            json={"expected_version": 2, "definition": definition},
        )
        self.assertEqual(changed.status_code, 200, changed.text)
        self.assertEqual(changed.json()["definition"], definition)
        self.assertEqual(changed.json()["version"], 3)
        self.assertEqual(
            (await self.client.get(path)).json()["export_settings"],
            created["export_settings"],
        )
        archived = await self.client.delete(
            path, headers=self.headers, params={"expected_version": 3}
        )
        self.assertEqual(archived.status_code, 204)
        self.assertEqual(
            (await self.client.get(path + "/schema")).json()["status"], "ARCHIVED"
        )
        denied = await self.client.put(
            path + "/schema/draft",
            headers=self.headers,
            json={"expected_version": 4, "definition": definition},
        )
        self.assertEqual(denied.status_code, 409)
        self.assertEqual(denied.json()["detail"]["code"], "FEED_ARCHIVED")

    async def test_schema_invalid_payload_limits_and_rollback(self) -> None:
        """Недопустимые данные, chunked-лимиты и ошибки локалей не оставляют записи."""
        from test.test_feed_builder_schema import source_schema_document

        await self.seed_schema_locales()
        created = await self.create()
        path = self.base + "/" + created["id"]
        definition = source_schema_document()
        invalid = []
        value = copy.deepcopy(definition)
        value["root"]["fields"][1]["key"] = value["root"]["fields"][0]["key"]
        invalid.append(value)
        value = copy.deepcopy(definition)
        value["root"]["fields"][0]["type_definition"]["locale"] = None
        invalid.append(value)
        value = copy.deepcopy(definition)
        value["root"]["fields"][0]["type_definition"]["locale"] = "xx-NotHere"
        invalid.append(value)
        value = copy.deepcopy(definition)
        value["root"]["fields"][0]["type_definition"]["value"]["source"][
            "path"
        ] = "item.regular_price"
        invalid.append(value)
        value = copy.deepcopy(definition)
        value["root"]["fields"][0]["type_definition"]["currency"] = "USD"
        invalid.append(value)
        value = copy.deepcopy(definition)
        value["root"]["fields"][0]["type_definition"]["value"]["source"][
            "path"
        ] = "item.password"
        invalid.append(value)
        for definition in invalid:
            result = await self.client.put(
                path + "/schema/draft",
                headers=self.headers,
                json={"expected_version": 1, "definition": definition},
            )
            self.assertEqual(result.status_code, 422, result.text)
            self.assertEqual((await self.client.get(path)).json(), created)
        duplicate = await self.client.put(
            path + "/schema/draft",
            headers=self.headers,
            json={"expected_version": 1, "definition": invalid[0]},
        )
        self.assertEqual(
            duplicate.json()["detail"]["field_id"],
            invalid[0]["root"]["fields"][1]["id"],
        )
        self.assertEqual(
            duplicate.json()["detail"]["path"],
            ["definition", "root", "fields", 1, "key"],
        )

        async def chunks():
            yield b"{" + b" " * (1024 * 1024)
            yield b"}"

        too_large = await self.client.put(
            path + "/schema/draft",
            headers=self.headers | {"Content-Type": "application/json"},
            content=chunks(),
        )
        self.assertEqual(too_large.status_code, 413, too_large.text)
        nested = await self.client.put(
            path + "/schema/draft",
            headers=self.headers | {"Content-Type": "application/json"},
            content=b"[" * 170 + b"0" + b"]" * 170,
        )
        self.assertEqual(nested.status_code, 422, nested.text)
        self.assertEqual((await self.client.get(path)).json(), created)

    async def test_schema_concurrent_settings_save_and_tenant_authorization(
        self,
    ) -> None:
        """Общая версия защищает схему/настройки, tenant и auth не обходятся через новый URL."""
        from test.test_feed_builder_schema import source_schema_document

        await self.seed_schema_locales()
        created = await self.create()
        path = self.base + "/" + created["id"]
        definition = source_schema_document()
        first, second = await asyncio.gather(
            self.client.put(
                path + "/schema/draft",
                headers=self.headers,
                json={"expected_version": 1, "definition": definition},
            ),
            self.client.patch(
                path,
                headers=self.headers,
                json={"expected_version": 1, "name": "Конкурентные настройки"},
            ),
        )
        self.assertEqual(sorted([first.status_code, second.status_code]), [200, 409])
        self.assertEqual((await self.client.get(path)).json()["version"], 2)
        self.assertEqual(
            (
                await self.client.put(
                    path + "/schema/draft",
                    json={"expected_version": 2, "definition": definition},
                )
            ).status_code,
            403,
        )
        self.app.state.authorization_service = DenyFeedAccess()
        self.assertEqual((await self.client.get(path + "/schema")).status_code, 403)
        self.assertEqual(
            (
                await self.client.get("/api/console/feed-builder/source-paths")
            ).status_code,
            403,
        )
        self.assertEqual(
            (
                await self.client.put(
                    path + "/schema/draft",
                    headers=self.headers,
                    json={"expected_version": 2, "definition": definition},
                )
            ).status_code,
            403,
        )
        del self.app.state.authorization_service
        self.app.state.test_context = replace(
            self.context,
            principal=replace(self.context.principal, tenant_id=str(self.other.uuid)),
        )
        await self.refresh_csrf()
        self.assertEqual((await self.client.get(path + "/schema")).status_code, 404)
        self.assertEqual(
            (
                await self.client.put(
                    path + "/schema/draft",
                    headers=self.headers,
                    json={"expected_version": 2, "definition": definition},
                )
            ).status_code,
            404,
        )

    async def test_schema_calculation_roundtrip_and_commit_failure_rollback(
        self,
    ) -> None:
        """Известный сложный AST не теряется; сбой commit не превращается в успех."""
        await self.seed_schema_locales()
        original = rich_feed()
        async with self.scoped_session() as session:
            await SqlAlchemyFeedRepository(session).add(original)
        path = self.base + "/" + str(original.id.uuid)
        read = (await self.client.get(path + "/schema")).json()
        definition = copy.deepcopy(read["definition"])
        definition["root"]["fields"][1]["label"] = "Подробное описание"
        with patch.object(
            UnitOfWork, "commit", side_effect=RuntimeError("test commit failure")
        ):
            with self.assertRaises(RuntimeError):
                await self.client.put(
                    path + "/schema/draft",
                    headers=self.headers,
                    json={"expected_version": 1, "definition": definition},
                )
        self.assertEqual((await self.client.get(path + "/schema")).json(), read)
        saved = await self.client.put(
            path + "/schema/draft",
            headers=self.headers,
            json={"expected_version": 1, "definition": definition},
        )
        self.assertEqual(saved.status_code, 200, saved.text)
        self.assertEqual(saved.json()["definition"], definition)

    async def test_http_create_list_get_patch_archive_and_repeat(self) -> None:
        """Проходит полный путь CRUD с сохранением настроек и логическим удалением."""
        created = await self.create()
        identifier = created["id"]
        item = self.base + "/" + identifier
        listing = await self.client.get(self.base)
        self.assertEqual(listing.status_code, 200, listing.text)
        self.assertEqual(listing.json()["total"], 1)
        self.assertEqual(listing.json()["items"][0]["fields_count"], 0)
        self.assertEqual(listing.json()["items"][0]["format"], "csv")
        details = await self.client.get(item)
        self.assertEqual(details.json(), created)
        noop = await self.client.patch(
            item,
            headers=self.headers,
            json={"expected_version": 1, "name": created["name"]},
        )
        self.assertEqual(noop.json(), created)
        changed = await self.client.patch(
            item,
            headers=self.headers,
            json={"expected_version": 1, "name": "Новый фид"},
        )
        self.assertEqual(changed.status_code, 200, changed.text)
        self.assertEqual(changed.json()["version"], 2)
        self.assertEqual(changed.json()["schema"], created["schema"])
        self.assertEqual(changed.json()["export_settings"], created["export_settings"])
        stale = await self.client.patch(
            item,
            headers=self.headers,
            json={"expected_version": 1, "name": "Устаревшее"},
        )
        self.assertEqual(stale.status_code, 409)
        deleted = await self.client.delete(
            item, params={"expected_version": 2}, headers=self.headers
        )
        self.assertEqual(deleted.status_code, 204, deleted.text)
        self.assertEqual(deleted.content, b"")
        repeated = await self.client.delete(
            item, params={"expected_version": 2}, headers=self.headers
        )
        self.assertEqual(repeated.status_code, 204)
        self.assertEqual((await self.client.get(self.base)).json()["total"], 0)
        archived = await self.client.get(item)
        self.assertEqual(archived.json()["status"], "ARCHIVED")
        self.assertEqual(archived.json()["version"], 3)
        self.assertEqual(
            (await self.client.get(self.base, params={"status": "ARCHIVED"})).json()[
                "total"
            ],
            1,
        )
        rejected = await self.client.patch(
            item,
            headers=self.headers,
            json={"expected_version": 3, "name": "Изменить архив"},
        )
        self.assertEqual(rejected.status_code, 409)
        duplicate = await self.client.post(
            self.base,
            headers=self.headers,
            json={
                "name": "Другой",
                "code": created["code"],
                "export_settings": {"format_settings": {"format": "csv"}},
            },
        )
        self.assertEqual(duplicate.status_code, 409, duplicate.text)
        async with self.scoped_session() as session:
            self.assertEqual(
                (
                    await session.execute(select(func.count()).select_from(FeedModel))
                ).scalar_one(),
                1,
            )

    async def test_tenant_isolation_and_independent_code_uniqueness(self) -> None:
        """ID другого tenant недоступен; одинаковый код допустим в разных схемах."""
        first = await self.create()
        self.app.state.test_context = replace(
            self.context,
            principal=replace(self.context.principal, tenant_id=str(self.other.uuid)),
        )
        self.assertEqual(
            (await self.client.get(self.base + "/" + first["id"])).status_code, 404
        )
        self.assertEqual((await self.client.get(self.base)).json()["total"], 0)
        await self.refresh_csrf()
        rejected = await self.client.patch(
            self.base + "/" + first["id"],
            headers=self.headers,
            json={"expected_version": 1, "name": "Чужой"},
        )
        self.assertEqual(rejected.status_code, 404)
        rejected = await self.client.delete(
            self.base + "/" + first["id"],
            params={"expected_version": 1},
            headers=self.headers,
        )
        self.assertEqual(rejected.status_code, 404)
        other = await self.create()
        self.assertNotEqual(first["id"], other["id"])
        self.app.state.test_context = self.context
        self.assertEqual((await self.client.get(self.base)).json()["total"], 1)

    async def test_duplicate_code_rolls_back_all_patch_changes(self) -> None:
        """Конфликт уникального кода не сохраняет уже изменённое название."""
        first = await self.create("first")
        second = await self.create("second")
        response = await self.client.patch(
            self.base + "/" + second["id"],
            headers=self.headers,
            json={
                "expected_version": 1,
                "name": "Не должно сохраниться",
                "code": first["code"],
            },
        )
        self.assertEqual(response.status_code, 409, response.text)
        result = (await self.client.get(self.base + "/" + second["id"])).json()
        self.assertEqual(result, second)

    async def test_concurrent_updates_accept_only_one_expected_version(self) -> None:
        """Два запроса с одной версией не перезаписывают результат друг друга."""
        created = await self.create()
        path = self.base + "/" + created["id"]
        responses = await asyncio.gather(
            *(
                self.client.patch(
                    path,
                    headers=self.headers,
                    json={"expected_version": 1, "name": name},
                )
                for name in ("Первый", "Второй")
            )
        )
        self.assertEqual(
            sorted(response.status_code for response in responses), [200, 409]
        )
        result = (await self.client.get(path)).json()
        self.assertEqual(result["version"], 2)
        self.assertIn(result["name"], ("Первый", "Второй"))

    async def test_formats_replaced_atomically_without_cross_format_settings(
        self,
    ) -> None:
        """CSV заменяется XML целиком, параметры старого формата не переносятся."""
        created = await self.create()
        response = await self.client.patch(
            self.base + "/" + created["id"],
            headers=self.headers,
            json={
                "expected_version": 1,
                "export_settings": {
                    "format_settings": {
                        "format": "xml",
                        "root_name": "offers",
                        "item_name": "offer",
                    }
                },
            },
        )
        self.assertEqual(response.status_code, 200, response.text)
        settings = response.json()["export_settings"]["format_settings"]
        self.assertEqual(
            settings,
            {
                "format": "xml",
                "root_name": "offers",
                "item_name": "offer",
                "encoding": "utf-8",
            },
        )
        self.assertNotIn("delimiter", settings)
        await self.create("xml-feed", xml=True)

    async def test_schema_survives_repository_and_http_metadata_update(self) -> None:
        """Существующая сложная схема и точные Decimal не теряются в CRUD настроек."""
        original = rich_feed()
        async with self.scoped_session() as session:
            await SqlAlchemyFeedRepository(session).add(original)
        path = self.base + "/" + str(original.id.uuid)
        before = (await self.client.get(path)).json()
        with patch.object(
            Feed, "restore", side_effect=AssertionError("query restored root")
        ):
            response = await self.client.get(path)
        self.assertEqual(response.status_code, 200)
        changed = await self.client.patch(
            path,
            headers=self.headers,
            json={"expected_version": 1, "name": "Сохранить схему"},
        )
        self.assertEqual(changed.status_code, 200, changed.text)
        self.assertEqual(changed.json()["schema"], before["schema"])
        async with self.scoped_session() as session:
            restored = await SqlAlchemyFeedRepository(session).get_for_update(
                original.id
            )
        self.assertEqual(restored.schema, original.schema)
        self.assertEqual(restored.version.value, 2)

    async def test_search_pagination_status_and_literal_wildcards(self) -> None:
        """Список имеет стабильный порядок и трактует поисковые wildcard как текст."""
        first = await self.create("first")
        second = await self.create("second")
        listing = (await self.client.get(self.base, params={"limit": 1})).json()
        self.assertEqual(listing["total"], 2)
        self.assertEqual(len(listing["items"]), 1)
        next_page = (
            await self.client.get(self.base, params={"limit": 1, "offset": 1})
        ).json()
        self.assertNotEqual(listing["items"][0]["id"], next_page["items"][0]["id"])
        self.assertEqual(
            (await self.client.get(self.base, params={"search": "SECOND"})).json()[
                "total"
            ],
            1,
        )
        self.assertEqual(
            (await self.client.get(self.base, params={"search": "%"})).json()["total"],
            0,
        )
        self.assertEqual(
            (await self.client.get(self.base, params={"search": "_"})).json()["total"],
            0,
        )
        for params in (
            {"limit": 0},
            {"limit": 101},
            {"offset": -1},
            {"status": "invalid"},
        ):
            self.assertEqual(
                (await self.client.get(self.base, params=params)).status_code, 422
            )

    async def test_auth_authorization_csrf_and_validation(self) -> None:
        """Проверяет доверенные границы и HTTP 422 для null без внутренних ошибок."""
        payload = {
            "name": "Фид",
            "code": "feed",
            "export_settings": {"format_settings": {"format": "csv"}},
        }
        self.assertEqual(
            (await self.client.post(self.base, json=payload)).status_code, 403
        )
        self.app.state.authorization_service = DenyFeedAccess()
        self.assertEqual(
            (
                await self.client.post(self.base, headers=self.headers, json=payload)
            ).status_code,
            403,
        )
        self.assertEqual((await self.client.get(self.base)).status_code, 403)
        del self.app.state.authorization_service
        self.app.state.test_context = replace(self.context, principal=None)
        self.assertEqual((await self.client.get(self.base)).status_code, 401)
        self.app.state.test_context = replace(
            self.context, principal=replace(self.context.principal, tenant_id=None)
        )
        self.assertEqual((await self.client.get(self.base)).status_code, 403)
        self.app.state.test_context = self.context
        created = await self.create()
        path = self.base + "/" + created["id"]
        for payload in (
            {"expected_version": 1, "name": None},
            {"expected_version": 1},
            {"expected_version": 1, "export_settings": None},
            {"expected_version": 1, "status": "ACTIVE"},
        ):
            response = await self.client.patch(path, headers=self.headers, json=payload)
            self.assertEqual(response.status_code, 422, response.text)
        for payload in (
            {"name": "Фид", "code": "bad", "export_settings": {}},
            {
                "name": "Фид",
                "code": "bad",
                "status": "ACTIVE",
                "export_settings": {"format_settings": {"format": "csv"}},
            },
        ):
            response = await self.client.post(
                self.base, headers=self.headers, json=payload
            )
            self.assertEqual(response.status_code, 422, response.text)
        self.assertEqual(
            (await self.client.delete(path, headers=self.headers)).status_code, 422
        )

    async def test_repository_cas_and_rollback(self) -> None:
        """Условный UPDATE отклоняет устаревшую версию и UoW откатывает сбой."""
        original = rich_feed()
        async with self.scoped_session() as session:
            await SqlAlchemyFeedRepository(session).add(original)
        changed = original.change_settings(
            name=FeedNameVO("Сохранённое"),
            code=original.code,
            export_settings=original.export_settings,
            now=NOW,
        )
        async with self.scoped_session() as session:
            await SqlAlchemyFeedRepository(session).save(
                changed, expected_version=FeedVersionVO(1)
            )
        with self.assertRaises(FeedVersionConflictError):
            async with self.scoped_session() as session:
                await SqlAlchemyFeedRepository(session).save(
                    changed, expected_version=FeedVersionVO(1)
                )
        with self.assertRaises(RuntimeError):
            async with self.scoped_session() as session:
                later = changed.change_settings(
                    name=FeedNameVO("Откат"),
                    code=changed.code,
                    export_settings=changed.export_settings,
                    now=NOW,
                )
                await SqlAlchemyFeedRepository(session).save(
                    later, expected_version=FeedVersionVO(2)
                )
                raise RuntimeError("rollback")
        async with self.scoped_session() as session:
            restored = await SqlAlchemyFeedRepository(session).get_for_update(
                original.id
            )
        self.assertEqual(restored.name, changed.name)
        self.assertEqual(restored.version.value, 2)

    async def test_migration_upgrades_existing_tenant_without_other_tables(
        self,
    ) -> None:
        """Обновляет существующий tenant с предыдущей версии и создаёт только fb_feeds."""
        schema = self.schemas[0]
        async with self.engine.begin() as connection:
            await self.migrator.downgrade(
                connection, schema, "0019_catalog_price_amounts"
            )
            self.assertIsNone(
                (
                    await connection.execute(
                        text("SELECT to_regclass(:name)"),
                        {"name": schema + ".fb_feeds"},
                    )
                ).scalar_one()
            )
            await self.migrator.upgrade(connection, schema)
            self.assertEqual(
                await self.migrator.current(connection, schema),
                (self.migrator.head(),),
            )
            tables = (
                (
                    await connection.execute(
                        text(
                            "SELECT table_name FROM information_schema.tables WHERE table_schema=:schema AND table_name LIKE 'fb_%'"
                        ),
                        {"schema": schema},
                    )
                )
                .scalars()
                .all()
            )
            self.assertEqual(tables, ["fb_feeds", "fb_publications"])


if __name__ == "__main__":
    unittest.main()
