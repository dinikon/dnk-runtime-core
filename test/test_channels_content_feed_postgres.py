"""Реальные HTTP/UoW/миграции XML-фида с контролируемым источником и storage."""

import asyncio
from dataclasses import replace
from unittest import TestLoader, TestSuite
from unittest.mock import AsyncMock, Mock, patch
from urllib.parse import urlsplit
from uuid import UUID
from xml.etree import ElementTree as ET

from fastapi import HTTPException
from sqlalchemy import update

from src.modules.channels.infrastructure.persistence.models.content_feed import (
    ContentFeedModel as F,
)
from src.modules.channels.infrastructure.persistence.models.content_media import (
    ContentMediaModel as M,
)
from src.modules.channels.infrastructure.persistence.models.external_publication import (
    ExternalPublicationModel as P,
)
from src.modules.channels.infrastructure.registry import InstalledPlatforms
from src.modules.channels.presentation.content_feed.assembly import (
    build_content_feed_runtime,
    ContentFeedRuntime,
)
from src.modules.channels.presentation.content_feed.depends import (
    get_content_feed_runtime,
)
from src.modules.channels.presentation.content_feed.router import public_router
from src.modules.channels.presentation.content_media.depends import MediaTenantDep
from src.modules.channels.presentation.content_feed.http.response.get_content_feed_xml import (
    GetContentFeedXmlResponse,
)
from src.modules.channels.infrastructure.content_feed.source import HttpsFeedSource
from src.modules.identity.presentation.access.depends import (
    default_authorization_service,
)
from src.modules.identity.presentation.auth.depends import (
    require_authenticated_request_context,
)
from src.modules.shared.presentation.persistence.depends import UoWDep
from src.modules.shared.infrastructure.time.utc_clock import UtcClock
from src.modules.shared.infrastructure.uuid.uuid7_generator import UUID7Generator
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_connection import (
    bind_tenant_schema,
)
from test.test_channels_content_media_postgres import ContentMediaPostgresTests
from test.test_channels_content_feed import XML


class ContentFeedPostgresTests(ContentMediaPostgresTests):
    async def asyncSetUp(self) -> None:
        """Собирает настоящий HTTP/UoW и подменяет только источник и storage."""
        await super().asyncSetUp()
        self.app.include_router(public_router)
        self.xml = XML
        self.source_entered = None
        self.source_release = None
        self.fetches = 0
        self.feed_source = Mock()
        self.feed_source.validate_url = HttpsFeedSource().validate_url

        async def runtime(uow: UoWDep, tenant: MediaTenantDep) -> ContentFeedRuntime:
            """Собирает реальные сценарии от общего UoW с тестовым источником."""

            async def fetch(url: str) -> bytes:
                """Возвращает управляемый исходник и проверяет границу транзакции."""
                self.assertFalse(
                    uow.session.in_transaction(), "Source HTTP inside SQL transaction"
                )
                self.fetches += 1
                if self.source_entered is not None:
                    self.source_entered.set()
                    await self.source_release.wait()
                return self.xml

            source = Mock(
                validate_url=self.feed_source.validate_url,
                fetch=AsyncMock(side_effect=fetch),
            )
            return build_content_feed_runtime(
                session=uow.session,
                tenant_id=tenant.id,
                base_url=tenant.base_url,
                uow=uow,
                cipher=self.cipher,
                clock=UtcClock(),
                uuid=UUID7Generator(),
                platforms=InstalledPlatforms(),
                storage=self.storage,
                authorization=getattr(
                    self.app.state,
                    "authorization_service",
                    default_authorization_service,
                ),
                source=source,
            )

        self.app.dependency_overrides[get_content_feed_runtime] = runtime

    async def setup_feed(
        self, *, media: bool = False, variable: bool = False
    ) -> tuple[str, str, str, dict, list[str]]:
        """Создаёт сохранённое разрешённое представление и выключенный фид."""
        if media:
            channel, group, root, detail, images = await self.media_fixture()
            pubs = [str(row["id"]) for row in await self.rows(P)]
        else:
            channel, group, root, _, pubs = await self.fixture(variable=variable)
            await self.verified(channel)
            detail = await self.call("GET", self.path(channel, group))
            detail = await self.call(
                "PUT",
                self.path(channel, group),
                self.version(detail) | {"overrides": {}},
            )
            await self.call(
                "POST", self.path(channel, group) + "/enable", self.version(detail)
            )
        async with self.sessions() as session:
            await bind_tenant_schema(
                await session.connection(), self.tenant, self.naming
            )
            for index, identifier in enumerate(pubs):
                await session.execute(
                    update(P)
                    .where(P.id == UUID(identifier))
                    .values(platform_data={"import_key": f"{index+1:03d}"})
                )
            await session.commit()
        value = (
            await self.call(
                "POST",
                f"/channels/{channel}/content-feeds",
                {"source_url": "https://supplier.example/source.xml?secret=hidden"},
                201,
            )
        )["feed"]
        return channel, group, root, value, pubs

    def feed_path(self, channel: str, value: dict) -> str:
        """Строит путь управления конкретным фидом."""
        return f'/channels/{channel}/content-feeds/{value["id"]}'

    async def enable_feed(self, channel: str, value: dict) -> dict:
        """Включает фид через настоящий HTTP и expected_revision."""
        return (
            await self.call(
                "POST",
                self.feed_path(channel, value) + "/enable",
                {"expected_revision": value["revision"]},
            )
        )["feed"]

    async def test_text_feed_current_catalog_and_full_source_preserved(self) -> None:
        """Отдаёт актуальный контент и сохраняет весь исходный ассортимент."""
        channel, group, root, value, _ = await self.setup_feed()
        self.assertFalse(value["enabled"])
        self.assertNotIn("hidden", str(value))
        stored = (await self.rows(F))[0]
        self.assertNotIn(b"hidden", stored["source_url_encrypted"])
        before = await self.rows(P)
        diagnostic = await self.call(
            "POST", self.feed_path(channel, value) + "/preview"
        )
        self.assertTrue(diagnostic["ready"], diagnostic)
        self.assertEqual(diagnostic["statistics"]["offers"], 2)
        self.assertEqual(await self.rows(M), [])
        value = await self.enable_feed(channel, value)
        response = await self.client.get(value["public_url"])
        self.assertEqual(response.status_code, 200, response.text)
        self.assertTrue(response.headers["content-type"].startswith("application/xml"))
        self.assertEqual(response.headers["cache-control"], "no-store")
        doc = ET.fromstring(response.content)
        first, second = doc.findall("./shop/offers/offer")
        self.assertEqual(first.get("id"), "001")
        self.assertEqual(first.findtext("name"), "Catalog ru")
        self.assertEqual(first.findtext("name_ua"), "Catalog uk")
        self.assertEqual(first.findtext("price"), "12.50")
        self.assertEqual(first.findtext("vendorCode"), "SKU-1")
        self.assertEqual(second.findtext("name"), "Unmatched")
        self.assertEqual(await self.rows(P), before)
        await self.set_content(root, "ru", "Changed catalog")
        updated = await self.client.get(value["public_url"])
        self.assertEqual(updated.status_code, 200, updated.text)
        self.assertEqual(
            ET.fromstring(updated.content).findtext("./shop/offers/offer/name"),
            "Changed catalog",
        )
        self.xml = self.xml.replace(
            b"</offers>",
            b'<offer id="003"><name>New source product</name><categoryId>1</categoryId></offer></offers>',
        )
        updated = await self.client.get(value["public_url"])
        self.assertEqual(
            len(ET.fromstring(updated.content).findall("./shop/offers/offer")), 3
        )

    async def test_gallery_reused_and_public_xml_and_image_need_no_console_session(
        self,
    ) -> None:
        """Переиспользует media и открывает разрешённые изображения без Console-сессии."""
        channel, _, _, value, _ = await self.setup_feed(media=True)
        value = await self.enable_feed(channel, value)
        media = await self.rows(M)
        self.assertEqual(len(media), 2)

        async def deny() -> None:
            """Доказывает отсутствие Console-аутентификации в публичном пути."""
            raise HTTPException(401)

        self.app.dependency_overrides[require_authenticated_request_context] = deny
        first = await self.client.get(value["public_url"])
        self.assertEqual(first.status_code, 200, first.text)
        urls = [
            node.text
            for node in ET.fromstring(first.content).findall(
                "./shop/offers/offer/picture"
            )
        ]
        self.assertEqual(len(urls), 2)
        image = await self.client.get(urls[0])
        self.assertEqual(image.status_code, 200, image.text)
        second = await self.client.get(value["public_url"])
        self.assertEqual(second.content, first.content)
        self.assertEqual(await self.rows(M), media)

    async def test_rotate_revoke_delete_and_revision_conflicts(self) -> None:
        """Проверяет отзыв ссылок, удаление и конфликты управления."""
        channel, _, _, value, _ = await self.setup_feed()
        value = await self.enable_feed(channel, value)
        path = self.feed_path(channel, value)
        old_url = value["public_url"]
        rotated = (
            await self.call(
                "POST",
                path + "/access/rotate",
                {"expected_revision": value["revision"]},
            )
        )["feed"]
        self.assertEqual((await self.client.get(old_url)).status_code, 404)
        self.assertEqual(
            (await self.client.get(rotated["public_url"])).status_code, 200
        )
        await self.call(
            "POST", path + "/disable", {"expected_revision": value["revision"]}, 409
        )
        revoked = (
            await self.call(
                "POST",
                path + "/access/revoke",
                {"expected_revision": rotated["revision"]},
            )
        )["feed"]
        self.assertFalse(revoked["enabled"])
        self.assertIsNone(revoked["public_url"])
        self.assertEqual(
            (await self.client.get(rotated["public_url"])).status_code, 404
        )
        await self.call(
            "DELETE", path + f'?expected_revision={revoked["revision"]}', status=204
        )
        self.assertEqual(await self.rows(F), [])
        self.assertEqual(
            (await self.client.get(rotated["public_url"])).status_code, 404
        )

    async def test_source_failure_never_returns_partial_xml_or_unmodified_fallback(
        self,
    ) -> None:
        """Не выдаёт частичный XML или молчаливый исходник при ошибках сборки."""
        channel, _, _, value, _ = await self.setup_feed()
        value = await self.enable_feed(channel, value)
        for broken in (
            b"<yml_catalog>",
            XML.replace(b'id="002"', b'id="001"'),
            XML.replace(b'id="001"', b'id="999"'),
            XML.replace(b"<offers>", b"<offers>").replace(
                b"<categoryId>2</categoryId>", b"<categoryId>missing</categoryId>"
            ),
        ):
            self.xml = broken
            response = await self.client.get(value["public_url"])
            self.assertEqual(response.status_code, 422, response.text)
            self.assertNotIn(b"<offer", response.content)
            self.assertNotIn("hidden", response.text)
            preview = await self.call(
                "POST", self.feed_path(channel, value) + "/preview"
            )
            self.assertFalse(preview["ready"])
            self.assertIsNone(preview["statistics"])

    async def test_missing_import_key_and_duplicate_native_keys_block_enable(
        self,
    ) -> None:
        """Не включает фид с неоднозначной адресацией существующих публикаций."""
        channel, _, _, value, pubs = await self.setup_feed(variable=True)
        async with self.sessions() as session:
            await bind_tenant_schema(
                await session.connection(), self.tenant, self.naming
            )
            await session.execute(
                update(P).where(P.id == UUID(pubs[0])).values(platform_data={})
            )
            await session.commit()
        result = await self.call("POST", self.feed_path(channel, value) + "/preview")
        self.assertEqual(result["issues"][0]["code"], "feed_import_key_missing")
        async with self.sessions() as session:
            await bind_tenant_schema(
                await session.connection(), self.tenant, self.naming
            )
            await session.execute(update(P).values(platform_data={"import_key": "001"}))
            await session.commit()
        result = await self.call("POST", self.feed_path(channel, value) + "/preview")
        self.assertEqual(result["issues"][0]["code"], "feed_import_key_duplicate")
        await self.call(
            "POST",
            self.feed_path(channel, value) + "/enable",
            {"expected_revision": value["revision"]},
            422,
        )
        self.assertFalse((await self.rows(F))[0]["enabled"])

    async def test_source_change_disables_unique_scope_and_noop_preserves_revision(
        self,
    ) -> None:
        """Проверяет уникальность области, сохранение без изменений и смену источника."""
        channel, _, _, value, _ = await self.setup_feed()
        value = await self.enable_feed(channel, value)
        path = self.feed_path(channel, value)
        same = (
            await self.call(
                "PUT",
                path,
                {
                    "expected_revision": value["revision"],
                    "source_url": "https://supplier.example/source.xml?secret=hidden",
                },
            )
        )["feed"]
        self.assertEqual(same, value)
        await self.call(
            "POST",
            f"/channels/{channel}/content-feeds",
            {"source_url": "https://supplier.example/other"},
            409,
        )
        changed = (
            await self.call(
                "PUT",
                path,
                {
                    "expected_revision": value["revision"],
                    "source_url": "https://supplier.example/changed.xml",
                },
            )
        )["feed"]
        self.assertFalse(changed["enabled"])
        self.assertEqual(changed["revision"], value["revision"] + 1)
        self.assertEqual((await self.client.get(value["public_url"])).status_code, 404)
        self.assertEqual(
            (await self.call("GET", f"/channels/{channel}/content-feeds"))["items"],
            [changed],
        )

    async def test_disabling_during_source_fetch_fences_result_without_sql_lock(
        self,
    ) -> None:
        """Позволяет выключить фид во время сети и отклоняет подготовленный результат."""
        channel, _, _, value, _ = await self.setup_feed()
        value = await self.enable_feed(channel, value)
        self.source_entered, self.source_release = asyncio.Event(), asyncio.Event()
        pending = asyncio.create_task(self.client.get(value["public_url"]))
        await asyncio.wait_for(self.source_entered.wait(), 5)
        try:
            disabled = await asyncio.wait_for(
                self.call(
                    "POST",
                    self.feed_path(channel, value) + "/disable",
                    {"expected_revision": value["revision"]},
                ),
                5,
            )
            self.assertFalse(disabled["feed"]["enabled"])
        finally:
            self.source_release.set()
        response = await pending
        self.assertEqual(response.status_code, 404, response.text)
        self.assertNotIn(b"<offer", response.content)

    async def test_other_tenant_wrong_token_permissions_and_channel_delete(
        self,
    ) -> None:
        """Проверяет tenant isolation, права и каскад удаления."""
        channel, _, _, value, _ = await self.setup_feed()
        value = await self.enable_feed(channel, value)
        parsed = urlsplit(value["public_url"])
        response = await self.client.get(parsed.path + "?token=wrong")
        self.assertEqual(response.status_code, 404)
        original = self.app.state.test_context
        self.app.state.test_context = replace(
            original, principal=replace(original.principal, tenant_id=str(self.other))
        )
        self.assertEqual((await self.client.get(value["public_url"])).status_code, 404)
        self.app.state.test_context = original

        class DenyFiles:
            async def can(self, **kwargs: object) -> bool:
                """Имитирует отзыв разрешений через публичный порт Identity."""
                return False

        self.app.state.authorization_service = DenyFiles()
        response = await self.client.get(value["public_url"])
        self.assertEqual(response.status_code, 403, response.text)
        del self.app.state.authorization_service
        detail = await self.call("GET", f"/channels/{channel}")
        await self.call(
            "DELETE",
            f'/channels/{channel}?expected_revision={detail["revision"]}',
            status=204,
        )
        self.assertEqual(await self.rows(F), [])

    async def test_variations_keep_original_offer_ids_and_group_structure(self) -> None:
        """Сохраняет исходную структуру разновидностей при наложении контента."""
        channel, _, _, value, _ = await self.setup_feed(variable=True)
        value = await self.enable_feed(channel, value)
        response = await self.client.get(value["public_url"])
        self.assertEqual(response.status_code, 200, response.text)
        first, second = ET.fromstring(response.content).findall("./shop/offers/offer")
        self.assertEqual((first.get("id"), second.get("id")), ("001", "002"))
        self.assertEqual(first.get("group_id"), "9")
        self.assertEqual(first.findtext("name"), second.findtext("name"))

    async def test_media_revocation_before_final_snapshot_blocks_complete_response(
        self,
    ) -> None:
        """Проверяет ревизию media после подготовки URL, а не только контент представления."""
        from datetime import UTC, datetime
        from src.modules.channels.infrastructure.content_feed.persistence.query_repository import (
            SqlAlchemyContentFeedQueryRepository,
        )

        channel, _, _, value, _ = await self.setup_feed(media=True)
        value = await self.enable_feed(channel, value)
        original = SqlAlchemyContentFeedQueryRepository.begin_snapshot
        calls = 0

        async def begin(repository: SqlAlchemyContentFeedQueryRepository) -> None:
            """Отзывает media непосредственно перед заключительным снимком."""
            nonlocal calls
            calls += 1
            if calls == 2:
                async with self.sessions() as session:
                    await bind_tenant_schema(
                        await session.connection(), self.tenant, self.naming
                    )
                    await session.execute(
                        update(M).values(
                            revision=M.revision + 1, access_revoked_at=datetime.now(UTC)
                        )
                    )
                    await session.commit()
            await original(repository)

        with patch.object(
            SqlAlchemyContentFeedQueryRepository, "begin_snapshot", begin
        ):
            response = await self.client.get(value["public_url"])
        self.assertEqual(response.status_code, 503, response.text)
        self.assertEqual(response.json()["detail"]["code"], "feed_media_changed")
        self.assertNotIn(b"<offer", response.content)

    async def test_migration_roundtrip_preserves_publications_and_catalog(self) -> None:
        """Миграция фида не меняет владельцев исходных публикаций и Catalog."""
        from src.modules.tenancy.infrastructure.tenant.persistence.tenant_migrations import (
            TenantMigrator,
        )

        channel, _, root, value, _ = await self.setup_feed()
        before = await self.rows(P)
        async with self.engine.begin() as connection:
            await TenantMigrator().downgrade(
                connection, self.schemas[0], "0013_channels_content_deliveries"
            )
            await TenantMigrator().upgrade(connection, self.schemas[0])
        self.assertEqual(await self.rows(P), before)
        self.assertEqual(await self.rows(F), [])
        await self.call("GET", f"/catalog/items/{root}?locale=uk")
        recreated = await self.call(
            "POST",
            f"/channels/{channel}/content-feeds",
            {"source_url": "https://supplier.example/source.xml"},
            201,
        )
        self.assertFalse(recreated["feed"]["enabled"])

    async def test_disabled_representation_is_passthrough_and_csrf_is_required(
        self,
    ) -> None:
        """Запрет наложения сохраняет исходный offer вместо удаления из ассортимента."""
        channel, group, _, value, _ = await self.setup_feed()
        value = await self.enable_feed(channel, value)
        response = await self.client.post(
            "/api/console" + self.feed_path(channel, value) + "/access/rotate",
            json={"expected_revision": value["revision"]},
        )
        self.assertEqual(response.status_code, 403)
        detail = await self.call("GET", self.path(channel, group))
        await self.call(
            "POST", self.path(channel, group) + "/disable", self.version(detail)
        )
        response = await self.client.get(value["public_url"])
        self.assertEqual(response.status_code, 200, response.text)
        offers = ET.fromstring(response.content).findall("./shop/offers/offer")
        self.assertEqual(len(offers), 2)
        self.assertEqual(offers[0].findtext("name"), "Old")


def load_tests(loader: TestLoader, tests: TestSuite, pattern: str | None) -> TestSuite:
    """Выбирает только новые сценарии без повторения унаследованных тестов."""
    return TestSuite(
        ContentFeedPostgresTests(name)
        for name in ContentFeedPostgresTests.__dict__
        if name.startswith("test_")
    )
