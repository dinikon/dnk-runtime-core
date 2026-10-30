"""Инварианты фида и нативная сериализация Prom без внешних запросов."""

from dataclasses import asdict, replace
from datetime import UTC, datetime
from unittest import TestCase, IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, Mock
from uuid import uuid4
from xml.etree import ElementTree as ET

from cryptography.fernet import Fernet

from src.modules.channels.application.content_feed.contracts import (
    RenderedFeed,
    FeedOverlay,
    FeedSnapshot,
    FeedGroupSnapshot,
    FeedPublicationKey,
)
from src.modules.channels.application.content_feed.error import FeedBuildError
from src.modules.channels.application.content_feed.service.renderer import FeedRenderer
from src.modules.channels.domain.content_feed.aggregate import ContentFeed
from src.modules.channels.domain.content_feed.error import ContentFeedError
from src.modules.channels.domain.content_feed.value_object import FeedSourceVO
from src.modules.channels.domain.product_representation.value_object import (
    ContentOrigins,
    FieldOrigin,
    ContentOrigin,
    LocalizedContent,
    PreparedPublicationContent,
    ContentTargetRole,
)
from src.modules.channels.infrastructure.content_feed.access_tokens import (
    EncryptedFeedTokens,
)
from src.modules.channels.infrastructure.content_feed.source import HttpsFeedSource
from src.modules.channels.infrastructure.platforms.prom.feed_serializer import (
    PromYmlSerializer,
)
from src.modules.channels.infrastructure.platforms.prom.publications import (
    PromPublicationReader,
)
from src.modules.channels.infrastructure.platforms.prom.models import PromConfig
from src.modules.shared.infrastructure.crypto.fernet_cipher import FernetCipher
from src.modules.shared.domain.value_object.entity_id import EntityIdVO

XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE yml_catalog SYSTEM "shops.dtd">
<yml_catalog date="2026-10-30 12:00"><shop><name>Shop</name><categories>
<category id="1">Root</category><category id="2" parentId="1" custom="keep">Child</category>
</categories><offers>
<offer id="001" group_id="9" available="true" strange="yes"><name>Old</name><description>Old body</description><categoryId>2</categoryId><price>12.50</price><currencyId>UAH</currencyId><quantity_in_stock>7</quantity_in_stock><vendorCode>SKU-1</vendorCode><param name="size">M</param><ext:unknown xmlns:ext="urn:test" flag="1">Keep<ext:child/>tail</ext:unknown><!--comment--></offer>
<offer id="002" available="false"><name>Unmatched</name><categoryId>1</categoryId><price>5</price></offer>
</offers><extension>Keep shop data</extension></shop></yml_catalog>"""


def target(
    *, title: str = "Название & <новое>", body: str = "<p>Текст & описание</p>"
) -> PreparedPublicationContent:
    """Создаёт многоязычное представление существующей публикации."""
    origin = FieldOrigin(ContentOrigin.CATALOG, EntityIdVO(uuid4()))
    origins = ContentOrigins(origin, origin, origin)
    return PreparedPublicationContent(
        EntityIdVO(uuid4()),
        "native-99",
        None,
        "simple",
        EntityIdVO(uuid4()),
        EntityIdVO(uuid4()),
        ContentTargetRole.POSITION,
        (
            LocalizedContent("ru", title, body, None, origins),
            LocalizedContent(
                "uk", "Українська назва", "<p>Український опис</p>", None, origins
            ),
        ),
        (),
    )


def feed(cipher: FernetCipher) -> ContentFeed:
    """Создаёт выключенный фид с зашифрованным источником."""
    now = datetime.now(UTC)
    return ContentFeed.create(
        identifier=EntityIdVO(uuid4()),
        connection_id=EntityIdVO(uuid4()),
        source=FeedSourceVO("prom.yml.v1", {"base_locale": "ru"}),
        source_url_encrypted=cipher.encrypt(
            b"https://supplier.example/source.xml?secret=hidden"
        ),
        token_hash=b"x" * 32,
        token_encrypted=b"token",
        actor=EntityIdVO(uuid4()),
        now=now,
    )


class ContentFeedDomainTests(TestCase):
    def setUp(self) -> None:
        """Готовит независимые исходники и зависимости сценария."""
        self.cipher = FernetCipher(Fernet.generate_key().decode())
        self.feed = feed(self.cipher)

    def test_lifecycle_noops_conflicts_and_source_disables(self) -> None:
        """Проверяет ревизии, идемпотентность, выключение и отзыв доступа."""
        value = self.feed
        args = {"actor": value.updated_by, "now": value.updated_at}
        self.assertEqual((value.revision, value.enabled), (1, False))
        value.disable(expected_revision=1, **args)
        self.assertEqual(value.revision, 1)
        value.enable(expected_revision=1, blockers=(), **args)
        self.assertEqual((value.revision, value.enabled), (2, True))
        value.change_source(
            source=value.source,
            encrypted_url=value.source_url_encrypted,
            expected_revision=2,
            **args,
        )
        self.assertEqual(value.revision, 2)
        before = asdict(value)
        with self.assertRaises(ContentFeedError):
            value.rotate_access_token(
                token_hash=b"bad", token_encrypted=b"e", expected_revision=2, **args
            )
        self.assertEqual(asdict(value), before)
        with self.assertRaises(ContentFeedError):
            value.disable(expected_revision=1, **args)
        self.assertEqual(asdict(value), before)
        value.change_source(
            source=value.source, encrypted_url=b"new", expected_revision=2, **args
        )
        self.assertEqual((value.revision, value.enabled), (3, False))
        value.revoke_access(expected_revision=3, **args)
        self.assertEqual(
            (value.revision, value.enabled, value.access_token_hash), (4, False, None)
        )
        with self.assertRaises(ContentFeedError):
            value.enable(expected_revision=4, blockers=(), **args)
        value.rotate_access_token(
            token_hash=b"y" * 32, token_encrypted=b"new", expected_revision=4, **args
        )
        self.assertFalse(value.enabled)

    def test_restore_rejects_inconsistent_state_and_mutation_is_atomic(self) -> None:
        """Отклоняет противоречивые состояния без частичного изменения агрегата."""
        value = self.feed
        original = asdict(value)
        values = dict(
            identifier=value.id,
            connection_id=value.connection_id,
            scope_key=value.scope_key,
            revision=value.revision,
            enabled=False,
            source=value.source,
            source_url_encrypted=value.source_url_encrypted,
            access_token_hash=value.access_token_hash,
            access_token_encrypted=value.access_token_encrypted,
            created_at=value.created_at,
            updated_at=value.updated_at,
            created_by=value.created_by,
            updated_by=value.updated_by,
        )
        for change in (
            {"revision": 0},
            {"revision": True},
            {
                "enabled": True,
                "access_token_hash": None,
                "access_token_encrypted": None,
            },
            {"access_token_encrypted": None},
        ):
            with self.subTest(change=change), self.assertRaises(ContentFeedError):
                ContentFeed.restore(**(values | change))
        self.assertEqual(asdict(value), original)

    def test_source_snapshot_and_limited_tokens(self) -> None:
        """Проверяет независимость снимка и ограниченный секрет ссылки."""
        settings = {"nested": {"values": [1]}}
        value = FeedSourceVO("test", settings)
        settings["nested"]["values"].append(2)
        copy = value.settings
        copy["nested"]["values"].append(3)
        self.assertEqual(value.settings, {"nested": {"values": [1]}})
        access = EncryptedFeedTokens(
            cipher=self.cipher, base_url="https://api.tenant.example"
        )
        digest, encrypted = access.issue()
        url = access.url(self.feed.id.uuid, encrypted)
        secret = url.split("token=")[1]
        self.assertTrue(access.matches(secret, digest))
        self.assertFalse(access.matches("wrong", digest))
        self.assertNotIn(secret.encode(), encrypted)
        self.assertIn("/feed.xml?token=", url)
        with self.assertRaises(FeedBuildError):
            EncryptedFeedTokens(cipher=self.cipher, base_url="https://localhost").url(
                self.feed.id.uuid, encrypted
            )


class PromFeedSerializerTests(TestCase):
    def setUp(self) -> None:
        """Готовит независимые исходники и зависимости сценария."""
        self.serializer = PromYmlSerializer()
        self.settings = FeedSourceVO("prom.yml.v1", {"base_locale": "ru"})
        self.target = target()
        self.overlay = FeedOverlay(
            self.target.publication_id.uuid,
            "001",
            self.target,
            (
                "https://api.tenant.example/image.png?token=a",
                "https://api.tenant.example/image2.png?token=b",
            ),
        )

    def render(
        self, source: bytes = XML, overlays: tuple[FeedOverlay, ...] | None = None
    ) -> RenderedFeed:
        """Вызывает тот же serializer с выбранным исходником и наложением."""
        return self.serializer.render(
            source=source,
            settings=self.settings,
            overlays=overlays if overlays is not None else (self.overlay,),
        )

    def test_full_document_content_languages_unknown_fields_and_order(self) -> None:
        """Сохраняет ассортимент, расширения и порядок при наложении двух языков."""
        value = self.render()
        original = self.serializer._parse(XML)
        result = self.serializer._parse(value.content)
        self.assertEqual(
            self.serializer._protected(original), self.serializer._protected(result)
        )
        offers = result.findall("./shop/offers/offer")
        self.assertEqual([v.get("id") for v in offers], ["001", "002"])
        self.assertEqual(offers[0].findtext("name"), self.target.content[0].title)
        self.assertEqual(offers[0].findtext("description"), self.target.content[0].body)
        self.assertEqual(offers[0].findtext("name_ua"), "Українська назва")
        self.assertEqual(
            [n.text for n in offers[0].findall("picture")], list(self.overlay.gallery)
        )
        self.assertEqual(
            ET.tostring(original.findall("./shop/offers/offer")[1]),
            ET.tostring(offers[1]),
        )
        self.assertIn(b"comment", value.content)
        self.assertEqual(
            (
                value.statistics.offers,
                value.statistics.changed_offers,
                value.statistics.categories,
            ),
            (2, 1, 2),
        )

    def test_key_not_native_id_missing_and_duplicate(self) -> None:
        """Не подставляет нативный ID и отклоняет отсутствующие или неоднозначные ключи."""
        for overlays in (
            (replace(self.overlay, import_key="native-99"),),
            (self.overlay, self.overlay),
        ):
            with self.subTest(overlays=overlays), self.assertRaises(FeedBuildError):
                self.render(overlays=overlays)
        for xml in (
            XML.replace(b'id="002"', b'id="001"'),
            XML.replace(
                b"<offers>",
                b'<offers><offer id="001"><name>X</name><categoryId>1</categoryId></offer>',
            ),
        ):
            with self.assertRaises(FeedBuildError):
                self.render(xml)

    def test_malformed_empty_xxe_unsafe_expansion_and_categories(self) -> None:
        """Отклоняет неполный XML, entities и противоречивые категории."""
        for xml in (
            b"",
            XML[:-30],
            b"<html>error</html>",
            XML.replace(b"<offers>", b"<offers>").replace(
                b"categoryId>2<", b"categoryId>404<"
            ),
            XML.replace(
                b'SYSTEM "shops.dtd"', b'[<!ENTITY x SYSTEM "file:///etc/passwd">]'
            ),
            XML.replace(b"<offers>", b"<offers>").replace(
                b"<name>Old</name>", b"<name>\x01</name>"
            ),
            XML.replace(b'id="1">Root', b'id="1" parentId="2">Root'),
        ):
            with self.subTest(xml=xml[:50]), self.assertRaises(FeedBuildError):
                self.render(xml)
        with self.assertRaises(FeedBuildError):
            self.render(
                XML.replace(
                    b'<offer id="001"', b'<offer type="vendor.model" id="001"'
                ).replace(
                    b"<name>Old</name>",
                    b"<vendor>V</vendor><model>M</model><name>Old</name>",
                )
            )

    def test_gallery_limit_clear_and_uk_pair_are_explicit_failures(self) -> None:
        """Отказывает явно при неподдерживаемой очистке и ограничениях галереи."""
        for gallery in ((), tuple("https://img.example/" + str(i) for i in range(11))):
            with self.assertRaises(FeedBuildError):
                self.render(overlays=(replace(self.overlay, gallery=gallery),))
        uk = replace(self.target.content[1], body="")
        with self.assertRaises(FeedBuildError) as error:
            self.render(
                overlays=(
                    replace(self.overlay, target=replace(self.target, content=(uk,))),
                )
            )
        self.assertEqual(error.exception.code, "feed_description_clear_unsupported")
        value = self.render(overlays=())
        self.assertEqual(value.statistics.changed_offers, 0)

    def test_prom_normalizes_external_key_without_using_native_id(self) -> None:
        """Сохраняет внешний ключ отдельно от ID площадки и полного raw."""
        reader = PromPublicationReader(Mock())
        raw = {"id": 123, "external_id": "001", "sku": "sku"}
        observation = reader.normalize(raw, PromConfig())
        self.assertEqual(observation.external_id, "123")
        self.assertEqual(observation.platform_data["import_key"], "001")
        self.assertEqual(observation.raw_data, raw)
        self.assertIsNone(
            reader.normalize({"id": 123}, PromConfig()).platform_data["import_key"]
        )

    def test_source_rejects_private_hosts_credentials_redirect_recursion(self) -> None:
        """Не разрешает внутренние адреса, credentials и рекурсию источника."""
        source = HttpsFeedSource()
        for url in (
            "http://supplier.example/xml",
            "https://localhost/xml",
            "https://127.0.0.1/xml",
            "https://user:secret@supplier.example/xml",
            "https://supplier.example/api/channels/content-feeds/id/feed.xml",
            "https://supplier.example/xml#secret",
        ):
            with self.subTest(url=url), self.assertRaises(FeedBuildError):
                source.validate_url(url)
        self.assertEqual(
            source.validate_url("https://supplier.example/xml?token=secret"),
            "https://supplier.example/xml?token=secret",
        )


class FeedRendererTests(IsolatedAsyncioTestCase):
    async def test_source_outside_transaction_and_no_gallery_calls_for_text(
        self,
    ) -> None:
        """Проверяет сетевую границу, отсутствие лишних media и пересборку снимка."""
        cipher = FernetCipher(Fernet.generate_key().decode())
        value = feed(cipher)
        candidate = target()
        snapshot = FeedSnapshot(
            value.connection_id.uuid,
            1,
            (FeedGroupSnapshot(uuid4(), 1, 1, 1, (candidate,)),),
            (FeedPublicationKey(candidate.publication_id.uuid, 1, "001"),),
        )
        uow = Mock(commit=AsyncMock(), rollback=AsyncMock())
        queries = Mock(begin_snapshot=AsyncMock())
        feeds = Mock(get=AsyncMock(return_value=value))
        representations = Mock(snapshot=AsyncMock(return_value=snapshot))
        source = Mock(fetch=AsyncMock(return_value=XML))
        galleries = Mock(prepare=AsyncMock())
        access = Mock(matches=Mock(return_value=True))
        authorization = Mock(require=AsyncMock())
        renderer = FeedRenderer(
            feeds=feeds,
            queries=queries,
            representations=representations,
            source=source,
            serializer=PromYmlSerializer(),
            galleries=galleries,
            access=access,
            authorization=authorization,
            cipher=cipher,
            uow=uow,
            tenant_id=uuid4(),
        )

        async def fetch(url: str) -> bytes:
            """Возвращает управляемый исходник и проверяет границу транзакции."""
            self.assertGreater(uow.commit.await_count, 0)
            self.assertIn("secret=hidden", url)
            return XML

        source.fetch.side_effect = fetch
        result = await renderer.render(feed=value, channel_id=uuid4(), actor_id=uuid4())
        self.assertEqual(result.statistics.changed_offers, 1)
        galleries.prepare.assert_not_called()
        self.assertEqual(representations.snapshot.await_count, 2)
        changed = replace(snapshot, channel_revision=2)
        representations.snapshot.side_effect = [snapshot, changed, snapshot, changed]
        with self.assertRaises(FeedBuildError) as error:
            await renderer.render(feed=value, channel_id=uuid4(), actor_id=uuid4())
        self.assertEqual(error.exception.code, "feed_context_changed")
        self.assertEqual(source.fetch.await_count, 3)

    async def test_missing_or_duplicate_publication_keys_fail_before_render(
        self,
    ) -> None:
        """Блокирует наложение при отсутствии или конфликте подтверждённых ключей."""
        candidate = target()
        group = FeedGroupSnapshot(uuid4(), 1, 1, 1, (candidate,))
        for publications in (
            (FeedPublicationKey(candidate.publication_id.uuid, 1, None),),
            (
                FeedPublicationKey(candidate.publication_id.uuid, 1, "001"),
                FeedPublicationKey(uuid4(), 1, "001"),
            ),
        ):
            with self.assertRaises(FeedBuildError):
                FeedRenderer._keys(FeedSnapshot(uuid4(), 1, (group,), publications))


class FeedSourceTransportTests(IsolatedAsyncioTestCase):
    async def test_safe_complete_fetch_errors_and_no_query_in_httpx_log(self) -> None:
        """Проверяет HTTP-отказы без утечки query источника в сообщения и логи."""
        import httpx
        from unittest.mock import patch
        from src.modules.channels.infrastructure.http import PublicHttpsTransport

        source = HttpsFeedSource()
        secret_url = "https://supplier.example/source.xml?token=hidden"
        response = httpx.Response(200, content=XML)
        with (
            patch.object(
                PublicHttpsTransport,
                "handle_async_request",
                AsyncMock(return_value=response),
            ),
            patch("httpx._client.logger.info") as log,
        ):
            self.assertEqual(await source.fetch(secret_url), XML)
            log.assert_not_called()
        for status in (301, 404, 500):
            with patch.object(
                PublicHttpsTransport,
                "handle_async_request",
                AsyncMock(return_value=httpx.Response(status, content=b"not xml")),
            ):
                with self.assertRaises(FeedBuildError) as error:
                    await source.fetch(secret_url)
                self.assertNotIn("hidden", str(error.exception))
        with patch.object(
            PublicHttpsTransport,
            "handle_async_request",
            AsyncMock(side_effect=httpx.ReadTimeout(secret_url)),
        ):
            with self.assertRaises(FeedBuildError) as error:
                await source.fetch(secret_url)
            self.assertEqual(error.exception.code, "feed_source_unavailable")
            self.assertNotIn("hidden", str(error.exception))

    async def test_xml_limits_invalid_output_and_profile_are_rejected(self) -> None:
        """Отклоняет превышение лимитов, неверный профиль и недопустимый итоговый XML."""
        from src.modules.channels.application.content_feed.contracts import (
            MAX_FEED_BYTES,
        )

        serializer = PromYmlSerializer()
        settings = FeedSourceVO("prom.yml.v1", {})
        for source in (
            b"x" * (MAX_FEED_BYTES + 1),
            b"<yml_catalog>" + b"<x>" * 130 + b"</x>" * 130 + b"</yml_catalog>",
        ):
            with self.assertRaises(FeedBuildError):
                serializer.render(source=source, settings=settings, overlays=())
        for config in (
            FeedSourceVO("prom.price_ua.v1", {}),
            FeedSourceVO("prom.yml.v1", {"base_locale": "uk"}),
        ):
            with self.assertRaises(FeedBuildError):
                serializer.render(source=XML, settings=config, overlays=())
        content = target(title="bad\x00title")
        with self.assertRaises(FeedBuildError):
            serializer.render(
                source=XML,
                settings=settings,
                overlays=(
                    FeedOverlay(content.publication_id.uuid, "001", content, None),
                ),
            )
        with self.assertRaises(FeedBuildError):
            HttpsFeedSource().validate_url(
                "https://supplier.example/api/%63hannels/content-feeds/id/feed.xml"
            )
