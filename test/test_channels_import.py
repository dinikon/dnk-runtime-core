"""Domain, плагины и сетевые ограничения полного чтения карточки."""

import asyncio
from dataclasses import replace
from datetime import UTC, datetime, timedelta
import socket
import unittest
from unittest.mock import AsyncMock, patch
from uuid import uuid4
import httpx
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.channels.domain.publication_import.aggregate import (
    PublicationImportPreparation,
)
from src.modules.channels.domain.publication_import.value_object.snapshot import (
    ImportSnapshotVO,
    ImportImageVO,
    PreparedImageVO,
)
from src.modules.channels.domain.error import (
    ChannelsConflictError,
    ChannelsValidationError,
)
from src.modules.channels.application.plugin_contract import (
    ResourceSettingsDTO,
    ReadPublicationDetailsInputDTO,
    ConnectionCredentialsDTO,
    HttpResultDTO,
)
from src.modules.channels.application.port.plugin_services import PluginCallError
from src.modules.channels.infrastructure.http.image_download import (
    HttpsPublicationImageDownloader,
)
from src.modules.channels.infrastructure.plugin.prom.read_publication_details import (
    PromReadPublicationDetailsPlugin,
)
from src.modules.channels.infrastructure.plugin.woocommerce.read_publication_details import (
    WooReadPublicationDetailsPlugin,
)
from src.modules.channels.application.publication_import.snapshot import (
    snapshot_for_import,
)
from test.channels_import_support import FullPublicationTransport, PNG


class PublicationImportDomainTests(unittest.TestCase):
    """Проверяет lifecycle независимо от SQL и worker plumbing."""

    def setUp(self) -> None:
        """Создаёт ограниченный снимок с порядком, отличающимся от сортировки JSONB."""
        self.now = datetime.now(UTC)
        self.preparation = PublicationImportPreparation.create(
            EntityIdVO(uuid4()),
            EntityIdVO(uuid4()),
            EntityIdVO(uuid4()),
            3,
            1,
            self.now,
        )
        self.snapshot = ImportSnapshotVO(
            {"uk": {"title": "Назва", "body": "<p>Опис</p>"}},
            (
                ImportImageVO("z", "https://images.example/z.png"),
                ImportImageVO("a", "https://images.example/a.png"),
            ),
            {},
            (),
        )

    def test_lifecycle_keeps_snapshot_order_and_only_retries_failed_image(self) -> None:
        """JSONB-порядок media не меняет галерею; retry сохраняет готовый file_id."""
        p = self.preparation
        self.assertTrue(p.begin(0, self.now))
        p.receive_snapshot(self.snapshot)
        p.media = dict(sorted(p.media.items()))
        self.assertEqual(p.pending_image(), "z")
        identifier = EntityIdVO(uuid4())
        p.receive_image("z", PreparedImageVO(identifier))
        p.receive_image("a", PreparedImageVO(error_code="image_network_error"))
        self.assertEqual(p.status, "ready")
        with self.assertRaises(ChannelsConflictError):
            p.consume(p.revision, ("z", "a"), self.now)
        p.retry(p.revision, self.now)
        self.assertEqual(p.media["z"].file_id, identifier)
        self.assertEqual(p.pending_image(), "a")
        self.assertTrue(p.begin(p.sequence, self.now))
        p.receive_image("a", PreparedImageVO(EntityIdVO(uuid4())))
        p.consume(p.revision, ("a", "z"), self.now)
        self.assertEqual(p.used_image_ids, ("a", "z"))
        with self.assertRaises(ChannelsConflictError):
            p.cleaned(("z",))

    def test_expiration_cancel_and_late_results(self) -> None:
        """Не принимает старый worker sequence и создание после отмены/истечения."""
        p = self.preparation
        self.assertFalse(p.begin(99, self.now))
        p.cancel(p.revision, self.now)
        self.assertFalse(p.begin(0, self.now))
        with self.assertRaises(ChannelsConflictError):
            p.ensure_current(self.now)
        p = PublicationImportPreparation.create(
            EntityIdVO(uuid4()),
            EntityIdVO(uuid4()),
            EntityIdVO(uuid4()),
            1,
            1,
            self.now,
        )
        self.assertFalse(p.begin(0, self.now + timedelta(days=1)))
        p.expire(self.now + timedelta(days=1))
        self.assertEqual(p.status, "expired")

    def test_snapshot_detaches_input_and_does_not_accept_missing_image_result(
        self,
    ) -> None:
        """Вложенные входные словари не могут подменить сохранённые тексты."""
        translations = {"uk": {"title": "Назва", "body": None}}
        snapshot = ImportSnapshotVO(translations, self.snapshot.images, {}, ())
        translations["uk"]["title"] = "Changed"
        self.assertEqual(snapshot.translations["uk"]["title"], "Назва")
        self.preparation.begin(0, self.now)
        self.preparation.receive_snapshot(snapshot)
        with self.assertRaises(ChannelsValidationError):
            self.preparation.receive_image("z", PreparedImageVO())


class PublicationDetailsPluginTests(unittest.IsolatedAsyncioTestCase):
    """Проверяет реальные DTO и независимость от технического extensions."""

    async def test_prom_reads_both_locales_and_deduplicates_main_image(self) -> None:
        """Один ответ с multilang сохраняет разные тексты, даже если scalar всегда ru."""
        credentials = AsyncMock()
        credentials.resolve.return_value = ConnectionCredentialsDTO({"token": "secret"})
        http = FullPublicationTransport()
        request = ReadPublicationDetailsInputDTO(
            ResourceSettingsDTO(
                "https://my.prom.ua", {"locales": ["ru", "uk"], "currency": "UAH"}
            ),
            "company:1000",
            "product",
            "102",
        )
        result = await PromReadPublicationDetailsPlugin(credentials, http).execute(
            request
        )
        snapshot = snapshot_for_import(result, ("ru", "uk"))
        self.assertNotEqual(
            snapshot.translations["uk"]["title"], snapshot.translations["ru"]["title"]
        )
        self.assertEqual(len(result.images), 2)
        self.assertNotEqual(
            snapshot.translations["uk"]["body"], snapshot.translations["ru"]["body"]
        )
        self.assertEqual(
            snapshot.values["titles"], {"ru": "Название с Prom", "uk": "Назва з Prom"}
        )
        self.assertEqual(len(http.calls), 1)
        with self.assertRaises(ChannelsValidationError):
            snapshot_for_import(result, ("uk",))

    async def test_prom_multilang_precedes_scalar_and_missing_locale_is_not_copied(
        self,
    ) -> None:
        """Явный перевод, пустота и отсутствие языка не подменяются базовым текстом."""
        credentials = AsyncMock()
        credentials.resolve.return_value = ConnectionCredentialsDTO({"token": "test"})
        request = ReadPublicationDetailsInputDTO(
            ResourceSettingsDTO(
                "https://my.prom.ua", {"locales": ["ru", "uk"], "currency": "UAH"}
            ),
            "company:1000",
            "product",
            "102",
        )
        scalar = {
            "id": 102,
            "name": "Scalar RU",
            "description": "<p>Scalar RU body</p>",
            "price": 10,
            "currency": "UAH",
        }
        for multilang, ru_title, uk_title, uk_body in (
            (
                {
                    "name_multilang": {
                        "ru": "<b>Русский</b>",
                        "uk": "<i>Українська</i>",
                    },
                    "description_multilang": {
                        "ru": "<p>Русское описание</p>",
                        "uk": "<p>Український опис</p><script>bad()</script>",
                    },
                },
                "Русский",
                "Українська",
                "Український опис",
            ),
            (
                {
                    "name_multilang": {"ru": "Русский"},
                    "description_multilang": {"ru": "<p>Русское описание</p>"},
                },
                "Русский",
                None,
                None,
            ),
            (
                {
                    "name_multilang": {"ru": "Русский", "uk": ""},
                    "description_multilang": {
                        "ru": "<p>Русское описание</p>",
                        "uk": "",
                    },
                },
                "Русский",
                "",
                "",
            ),
            (
                {
                    "name_multilang": {"ru": None, "uk": None},
                    "description_multilang": {"ru": None, "uk": None},
                },
                None,
                None,
                None,
            ),
            ({}, "Scalar RU", None, None),
        ):
            with self.subTest(multilang=multilang):
                http = AsyncMock()
                http.get.return_value = HttpResultDTO(
                    {"product": {**scalar, **multilang}}, {}
                )
                result = await PromReadPublicationDetailsPlugin(
                    credentials, http
                ).execute(request)
                ru, uk = result.translations
                self.assertEqual(ru.title, ru_title)
                self.assertEqual(result.core.title, ru_title)
                self.assertEqual(uk.title, uk_title)
                if uk_body is None:
                    self.assertIsNone(uk.body)
                else:
                    self.assertIn(uk_body, uk.body)
                self.assertNotIn("<script", uk.body or "")
                http.get.assert_awaited_once()
                self.assertEqual(
                    http.get.await_args.kwargs["headers"]["X-LANGUAGE"], "ru"
                )

    async def test_prom_rejects_malformed_multilang_containers(self) -> None:
        """Повреждённый языковой объект не превращается в правдоподобный перевод."""
        credentials = AsyncMock()
        credentials.resolve.return_value = ConnectionCredentialsDTO({"token": "test"})
        request = ReadPublicationDetailsInputDTO(
            ResourceSettingsDTO(
                "https://my.prom.ua", {"locales": ["ru", "uk"], "currency": "UAH"}
            ),
            "company:1000",
            "product",
            "102",
        )
        for field in ("name_multilang", "description_multilang"):
            for value in ([], "not-a-language-map", True):
                with self.subTest(field=field, value=value):
                    http = AsyncMock()
                    http.get.return_value = HttpResultDTO(
                        {"product": {"id": 102, "name": "Scalar", field: value}}, {}
                    )
                    with self.assertRaises(PluginCallError) as error:
                        await PromReadPublicationDetailsPlugin(
                            credentials, http
                        ).execute(request)
                    self.assertEqual(
                        error.exception.reason_code, "invalid_publication_translation"
                    )

    async def test_woo_variation_inherits_explicitly_and_sanitizes_html(self) -> None:
        """Передаёт происхождение наследования и удаляет исполняемый HTML до Console."""
        credentials = AsyncMock()
        credentials.resolve.return_value = ConnectionCredentialsDTO(
            {"consumer_key": "key", "consumer_secret": "secret"}
        )
        request = ReadPublicationDetailsInputDTO(
            ResourceSettingsDTO(
                "https://shop.example", {"locales": ["uk"], "currency": "UAH"}
            ),
            "shop.example",
            "variation",
            "21",
            {"parent_id": 20},
        )
        result = await WooReadPublicationDetailsPlugin(
            credentials, FullPublicationTransport()
        ).execute(request)
        self.assertIn("description_inherited_from_parent", result.warnings)
        self.assertIn("gallery_inherited_from_parent", result.warnings)
        self.assertNotIn("<script", result.translations[0].body)
        self.assertEqual(len(result.images), 2)
        with self.assertRaises(PluginCallError):
            await WooReadPublicationDetailsPlugin(
                credentials, FullPublicationTransport()
            ).execute(replace(request, provider_context={}))


class PublicationImageDownloadTests(unittest.IsolatedAsyncioTestCase):
    """Проверяет DNS pinning, отсутствие секретов и ограниченный raster transport."""

    async def test_private_dns_and_non_https_are_rejected(self) -> None:
        """Не отправляет HTTP на localhost, приватную сеть или небезопасную схему."""
        downloader = HttpsPublicationImageDownloader()
        for url in (
            "http://images.example/a.png",
            "https://user:secret@images.example/a.png",
            "https://images.example:8443/a.png",
        ):
            with self.assertRaises(PluginCallError):
                await downloader.download(url)
        loop = asyncio.get_running_loop()
        with patch.object(
            loop,
            "getaddrinfo",
            AsyncMock(
                return_value=[
                    (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 443))
                ]
            ),
        ):
            with self.assertRaises(PluginCallError) as caught:
                await downloader.download("https://images.example/a.png")
            self.assertEqual(caught.exception.reason_code, "unsafe_image_url")

    async def test_no_credentials_redirects_and_size_limit(self) -> None:
        """Выбранный IP используется с исходным Host и SNI, без Authorization/Cookie."""
        real_client = httpx.AsyncClient
        payload = PNG

        def response(request: httpx.Request) -> httpx.Response:
            self.assertEqual(request.url.host, "93.184.216.34")
            self.assertEqual(request.headers["Host"], "images.example")
            self.assertEqual(request.headers["Accept"], "*/*")
            self.assertNotIn("authorization", request.headers)
            self.assertNotIn("cookie", request.headers)
            self.assertEqual(request.extensions["sni_hostname"], "images.example")
            return httpx.Response(
                200, content=payload, headers={"content-type": "image/jpeg"}
            )

        transport = httpx.MockTransport(response)
        loop = asyncio.get_running_loop()
        with (
            patch.object(
                loop,
                "getaddrinfo",
                AsyncMock(
                    return_value=[
                        (
                            socket.AF_INET,
                            socket.SOCK_STREAM,
                            6,
                            "",
                            ("93.184.216.34", 443),
                        )
                    ]
                ),
            ),
            patch(
                "httpx.AsyncClient",
                side_effect=lambda **kwargs: real_client(transport=transport, **kwargs),
            ),
        ):
            downloaded = await HttpsPublicationImageDownloader().download(
                "https://images.example/a.png"
            )
            self.assertEqual(downloaded.data, PNG)
            self.assertEqual(downloaded.content_type, "image/png")
            with self.assertRaises(PluginCallError) as caught:
                await HttpsPublicationImageDownloader(max_bytes=8).download(
                    "https://images.example/a.png"
                )
            self.assertEqual(caught.exception.reason_code, "image_too_large")
            payload = b"<html>not an image</html>"
            with self.assertRaises(PluginCallError) as caught:
                await HttpsPublicationImageDownloader().download(
                    "https://images.example/a.png"
                )
            self.assertEqual(caught.exception.reason_code, "invalid_image_file")
