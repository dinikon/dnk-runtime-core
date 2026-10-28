"""Domain, источники и проекции первого среза публикаций Channels."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
import json
from pathlib import Path
import unittest
from urllib.parse import parse_qs, urlsplit
from uuid import uuid4

from src.modules.channels.application.error import (
    ChannelInputError,
    VerificationFailure,
)
from src.modules.channels.application.external_publication.port.query_repository import (
    PublicationReadRow,
)
from src.modules.channels.application.external_publication.representation import (
    build_card,
)
from src.modules.channels.application.sync_run.port.source import (
    PublicationCheckpoint,
    PublicationReadPhase,
)
from src.modules.channels.domain.channel.value_object.connection_config import (
    ConnectionConfigVO,
)
from src.modules.channels.domain.external_publication.aggregate import (
    ExternalPublication,
    PublicationStructurePolicy,
)
from src.modules.channels.domain.external_publication.error import (
    InvalidExternalPublicationError,
)
from src.modules.channels.domain.external_publication.value_object import (
    PublicationData,
    PublicationKind,
    PublicationTitle,
)
from src.modules.channels.domain.sync_run.aggregate import SyncRun, SyncRunStatus
from src.modules.channels.domain.sync_run.error import InvalidSyncRunError
from src.modules.channels.infrastructure.http import JsonHttpResponse
from src.modules.channels.infrastructure.registry import InstalledPlatforms
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from test.test_channels import FixtureHttp

FIXTURES = Path(__file__).parent / "fixtures/channels"


def fixture(name: str) -> dict | list:
    """Читает обезличенный контрактный ответ."""
    return json.loads((FIXTURES / name).read_text())


class PageHttp(FixtureHttp):
    """Добавляет заголовки пагинации к существующему тестовому transport."""

    async def request_response(
        self, method: str, url: str, **kwargs: object
    ) -> JsonHttpResponse:
        """Сохраняет вызов и возвращает метаданные тестового ответа."""
        result = await self.request(method, url, **kwargs)
        return (
            result
            if isinstance(result, JsonHttpResponse)
            else JsonHttpResponse(result, {"x-wp-totalpages": "1"})
        )


class PublicationDomainTests(unittest.TestCase):
    """Проверяет инварианты без SQL и моделей платформ."""

    def setUp(self) -> None:
        """Готовит общие значения доменных сценариев."""
        self.now = datetime.now(UTC)
        self.connection = EntityIdVO(uuid4())
        self.run_id = EntityIdVO(uuid4())
        self.data = PublicationData(
            (PublicationTitle("uk", "Назва"),),
            "UAH",
            price=Decimal("0"),
            quantity=Decimal("0"),
            stock_mode="own",
        )

    def publication(
        self,
        *,
        kind: PublicationKind = PublicationKind.SIMPLE,
        parent_id: EntityIdVO | None = None,
        connection_id: EntityIdVO | None = None,
    ) -> ExternalPublication:
        """Создаёт доменный снимок через публичную фабрику."""
        return ExternalPublication.create(
            publication_id=EntityIdVO(uuid4()),
            connection_id=connection_id or self.connection,
            resource_type="product",
            external_id=str(uuid4()),
            kind=kind,
            parent_id=parent_id,
            raw_data={"nested": {"values": [0, None]}},
            data=self.data,
            platform_schema="test.v1",
            platform_data={},
            run_id=self.run_id,
            now=self.now,
        )

    def test_snapshot_isolation_and_revision_counts(self) -> None:
        """Вложенный словарь не меняет агрегат; одинаковый снимок не повышает ревизию."""
        raw = {"nested": {"values": [0, None]}}
        publication = self.publication()
        publication.observe(
            kind=PublicationKind.SIMPLE,
            parent_id=None,
            raw_data=raw,
            data=self.data,
            platform_schema="test.v1",
            platform_data={},
            run_id=self.run_id,
            now=self.now,
        )
        self.assertEqual(publication.revision, 1)
        raw["nested"]["values"].append("outside")
        returned = publication.raw_data
        returned["nested"]["values"].append("returned")
        self.assertEqual(publication.raw_data, {"nested": {"values": [0, None]}})
        publication.observe(
            kind=PublicationKind.SIMPLE,
            parent_id=None,
            raw_data=publication.raw_data,
            data=replace(self.data, price=Decimal("12.34")),
            platform_schema="test.v1",
            platform_data={},
            run_id=self.run_id,
            now=self.now,
        )
        self.assertEqual(publication.revision, 2)
        before = publication.raw_data
        with self.assertRaises(InvalidExternalPublicationError):
            publication.observe(
                kind=PublicationKind.VARIANT,
                parent_id=publication.id,
                raw_data={"changed": True},
                data=self.data,
                platform_schema="test.v1",
                platform_data={},
                run_id=self.run_id,
                now=self.now,
            )
        self.assertEqual(publication.revision, 2)
        self.assertEqual(publication.raw_data, before)

    def test_parent_roles_connection_and_depth_are_domain_rules(self) -> None:
        """Отклоняет чужой корень, второй уровень и неподходящую роль родителя."""
        root = self.publication()
        child = self.publication(kind=PublicationKind.VARIANT, parent_id=root.id)
        policy = PublicationStructurePolicy()
        policy.ensure_valid((root, child), required_parent_kind=PublicationKind.SIMPLE)
        with self.assertRaises(InvalidExternalPublicationError):
            policy.ensure_valid(
                (root, child), required_parent_kind=PublicationKind.VARIABLE
            )
        wrong_connection = self.publication(
            kind=PublicationKind.VARIANT,
            parent_id=root.id,
            connection_id=EntityIdVO(uuid4()),
        )
        with self.assertRaises(InvalidExternalPublicationError):
            policy.ensure_valid((root, wrong_connection))
        grandchild = self.publication(kind=PublicationKind.VARIANT, parent_id=child.id)
        with self.assertRaises(InvalidExternalPublicationError):
            policy.ensure_valid((root, child, grandchild))

    def test_restore_rejects_contradictory_publication(self) -> None:
        """Mapper не должен исправлять противоречия роли и связи."""
        for kind, parent in [
            (PublicationKind.VARIANT, None),
            (PublicationKind.SIMPLE, EntityIdVO(uuid4())),
        ]:
            with (
                self.subTest(kind=kind),
                self.assertRaises(InvalidExternalPublicationError),
            ):
                self.publication(kind=kind, parent_id=parent)
        with self.assertRaises(InvalidExternalPublicationError):
            PublicationData(
                (PublicationTitle("uk", "A"), PublicationTitle("uk", "B")), "UAH"
            )

    def test_sync_lifecycle_checkpoint_and_stale_generations(self) -> None:
        """Проверяет запуск, атомарность неудачной страницы и завершение поколения."""
        job_id = EntityIdVO(uuid4())
        run = SyncRun.create(
            run_id=self.run_id,
            connection_id=self.connection,
            config_revision=1,
            job_id=job_id,
            automatic=True,
            now=self.now,
        )
        run.start(now=self.now)
        revision = run.revision
        with self.assertRaises(InvalidSyncRunError):
            run.apply_page(
                checkpoint={"bad": True},
                processed=1,
                skipped=2,
                next_job_id=EntityIdVO(uuid4()),
                now=self.now,
            )
        self.assertEqual(run.revision, revision)
        self.assertEqual(run.checkpoint, {})
        checkpoint = {"cursor": {"page": 2}}
        next_job = EntityIdVO(uuid4())
        run.apply_page(
            checkpoint=checkpoint,
            processed=2,
            skipped=1,
            next_job_id=next_job,
            now=self.now,
        )
        checkpoint["cursor"]["page"] = 99
        self.assertEqual(run.checkpoint["cursor"]["page"], 2)
        self.assertFalse(run.accepts(job_id=job_id, config_revision=1))
        self.assertFalse(run.accepts(job_id=next_job, config_revision=2))
        run.apply_page(
            checkpoint={}, processed=0, skipped=0, next_job_id=None, now=self.now
        )
        self.assertEqual(run.status, SyncRunStatus.COMPLETED)
        self.assertFalse(run.active)
        with self.assertRaises(InvalidSyncRunError):
            run.start(now=self.now)

    def test_sync_restore_rejects_terminal_without_timestamp(self) -> None:
        """Проверяет обязательное время завершения и положительные ревизии."""
        values = dict(
            run_id=self.run_id,
            connection_id=self.connection,
            config_revision=1,
            revision=1,
            status=SyncRunStatus.FAILED,
            current_job_id=EntityIdVO(uuid4()),
            checkpoint={},
            processed_count=0,
            skipped_count=0,
            pages_count=0,
            automatic=False,
            error_code="failed",
            created_at=self.now,
            started_at=None,
            finished_at=None,
        )
        with self.assertRaises(InvalidSyncRunError):
            SyncRun.restore(**values)
        values.update(status=SyncRunStatus.QUEUED, error_code=None, config_revision=0)
        with self.assertRaises(InvalidSyncRunError):
            SyncRun.restore(**values)

    def test_prom_and_woocommerce_card_membership(self) -> None:
        """Корень Prom входит в выбор; контейнер WooCommerce не становится товаром."""
        root = PublicationReadRow(
            uuid4(), "201", PublicationKind.SIMPLE, None, self.data, 1, self.now, 1
        )
        child = PublicationReadRow(
            uuid4(),
            "202",
            PublicationKind.VARIANT,
            root.id,
            replace(self.data, titles=(PublicationTitle("uk", "Варіант"),)),
            1,
            self.now,
            1,
        )
        card = build_card(
            root=root,
            children=(child,),
            locale="uk",
            config_revision=1,
            selected_id=child.id,
        )
        self.assertEqual([item.id for item in card.items], [root.id, child.id])
        self.assertEqual(card.title, "Варіант")
        variable = replace(
            root,
            kind=PublicationKind.VARIABLE,
            data=replace(self.data, quantity=Decimal("20")),
        )
        inherited = replace(
            child,
            data=replace(
                self.data,
                titles=(PublicationTitle("uk", None),),
                inherit_title=True,
                stock_mode="parent",
                quantity=None,
            ),
        )
        card = build_card(
            root=variable, children=(inherited,), locale="uk", config_revision=2
        )
        self.assertEqual(len(card.items), 1)
        self.assertEqual(card.items[0].quantity, "20")
        self.assertTrue(card.items[0].stale_configuration)
        self.assertEqual(
            build_card(
                root=variable, children=(inherited,), locale="ru", config_revision=1
            ).title,
            None,
        )

    def test_woocommerce_card_title_does_not_follow_selected_variation(self) -> None:
        """Название контейнера сохраняется в списке и при прямой ссылке на вариацию."""
        root = PublicationReadRow(
            uuid4(),
            "275",
            PublicationKind.VARIABLE,
            None,
            replace(
                self.data,
                titles=(PublicationTitle("uk", "CRM Демо — Футболка Active"),),
                sku="CRM-PARENT",
                main_image_url="https://shop.example/parent.jpg",
            ),
            1,
            self.now,
            1,
        )
        children = tuple(
            PublicationReadRow(
                uuid4(),
                external_id,
                PublicationKind.VARIANT,
                root.id,
                replace(self.data, titles=(PublicationTitle("uk", title),)),
                1,
                self.now,
                1,
            )
            for external_id, title in (("276", "червоний, L"), ("277", "червоний, M"))
        )
        for selected_id in (None, root.id, children[0].id, children[1].id):
            with self.subTest(selected_id=selected_id):
                card = build_card(
                    root=root,
                    children=children,
                    locale="uk",
                    config_revision=1,
                    selected_id=selected_id,
                )
                self.assertEqual(card.title, "CRM Демо — Футболка Active")
                self.assertEqual(card.root_external_id, "275")
                self.assertEqual(card.root_sku, "CRM-PARENT")
                self.assertEqual(
                    card.root_main_image_url, "https://shop.example/parent.jpg"
                )
                self.assertIsNone(card.items[0].sku)
                self.assertIsNone(card.items[0].main_image_url)
                self.assertEqual(
                    [item.title for item in card.items], ["червоний, L", "червоний, M"]
                )
                self.assertEqual(
                    card.selected_publication_id,
                    (
                        selected_id
                        if selected_id in (children[0].id, children[1].id)
                        else children[0].id
                    ),
                )

        untranslated_root = replace(root, data=replace(root.data, titles=()))
        card = build_card(
            root=untranslated_root,
            children=children,
            locale="uk",
            config_revision=1,
        )
        self.assertIsNone(card.title)
        self.assertEqual(card.items[0].title, "червоний, L")


class PublicationPlatformTests(unittest.IsolatedAsyncioTestCase):
    """Проверяет готовые read-контракты всех трёх пакетов."""

    def config(self, kind: str, settings: dict | None = None) -> ConnectionConfigVO:
        """Создаёт вход конфигурации соответствующего пакета."""
        endpoint = {
            "prom": "https://my.prom.ua",
            "rozetka": "https://api-seller.rozetka.com.ua",
            "woocommerce": "https://shop.example/wordpress",
        }[kind]
        return ConnectionConfigVO.create(
            version=1, endpoint=endpoint, settings=settings or {}
        )

    def test_fixed_and_single_settings(self) -> None:
        """Не принимает другую валюту и неполный набор языков фиксированных площадок."""
        registry = InstalledPlatforms()
        for kind in ("prom", "rozetka"):
            platform = registry.get(kind)
            self.assertEqual(
                platform.validate(self.config(kind), None).config.settings,
                {"currency": "UAH", "locales": ["uk", "ru"]},
            )
            for settings in (
                {"currency": "USD"},
                {"locales": ["uk"]},
                {"locales": ["uk", "uk"]},
                {"locales": ["uk", "ru", "en"]},
            ):
                with (
                    self.subTest(kind=kind, settings=settings),
                    self.assertRaises(ChannelInputError),
                ):
                    platform.validate(self.config(kind, settings), None)
        for currency in ("UAH", "USD", "EUR"):
            for locale in ("uk", "ru", "en"):
                value = registry.get("woocommerce").validate(
                    self.config(
                        "woocommerce", {"currency": currency, "locale": locale}
                    ),
                    None,
                )
                self.assertEqual((value.currency, value.locales), (currency, (locale,)))
        for settings in (
            {"currency": "GBP"},
            {"locale": "de"},
            {"currency": ["UAH", "USD"]},
            {"locale": ["uk", "ru"]},
        ):
            with self.assertRaises(ChannelInputError):
                registry.get("woocommerce").validate(
                    self.config("woocommerce", settings), None
                )

    async def test_prom_parent_loading_raw_and_currency_policy(self) -> None:
        """Дозагружает основной товар, сохраняет raw и не конвертирует исходную USD."""
        child = fixture("prom-child.json")["product"]
        http = PageHttp([{"products": [child]}, fixture("prom-parent.json")])
        platform = InstalledPlatforms(http).get("prom")
        validated = platform.validate(
            self.config("prom"), {"token": "private-prom-token"}
        )
        page = await platform.read_publications(
            config=validated.config,
            credentials=validated.credentials,
            checkpoint=PublicationCheckpoint(),
        )
        self.assertTrue(page.done)
        self.assertEqual(page.items[0].kind, PublicationKind.VARIANT)
        self.assertEqual(page.dependencies[0].kind, PublicationKind.SIMPLE)
        self.assertEqual(page.items[0].data.price, Decimal("850"))
        self.assertEqual(page.items[0].data.currency, "UAH")
        self.assertEqual(page.items[0].platform_data["source_currency"], "USD")
        self.assertEqual(page.items[0].data.titles[1].title, None)
        self.assertEqual(
            page.dependencies[0].raw_data["unknown_native"]["nested"], ["keep", 0, None]
        )
        self.assertTrue(http.calls[1][1].endswith("/products/201"))
        self.assertNotIn("private-prom-token", http.calls[0][1])

    async def test_woocommerce_supported_types_pagination_and_parent_stock(
        self,
    ) -> None:
        """Пропускает grouped/external/расширения и отдельно читает вариации."""
        http = PageHttp(
            [
                {"settings": {"currency": "EUR"}},
                fixture("woocommerce-products.json"),
                fixture("woocommerce-variations.json"),
            ]
        )
        platform = InstalledPlatforms(http).get("woocommerce")
        validated = platform.validate(
            self.config("woocommerce", {"currency": "USD", "locale": "en"}),
            {"consumer_key": "ck-private", "consumer_secret": "cs-private"},
        )
        products = await platform.read_publications(
            config=validated.config,
            credentials=validated.credentials,
            checkpoint=PublicationCheckpoint(),
        )
        self.assertEqual((len(products.items), products.skipped_count), (2, 3))
        self.assertEqual(products.checkpoint.phase, PublicationReadPhase.CHILDREN)
        self.assertEqual(products.items[0].data.price, Decimal("0.00"))
        self.assertEqual(products.items[0].data.quantity, Decimal("0"))
        self.assertTrue(products.items[0].platform_data["virtual"])
        self.assertEqual(products.items[0].platform_data["source_currency"], "EUR")
        variants = await platform.read_publications(
            config=validated.config,
            credentials=validated.credentials,
            checkpoint=products.checkpoint,
            parent_external_id="510",
        )
        self.assertEqual(variants.items[1].data.stock_mode, "parent")
        self.assertIsNone(variants.items[1].data.quantity)
        self.assertEqual(variants.items[1].parent_external_id, "510")
        finished = await platform.read_publications(
            config=validated.config,
            credentials=validated.credentials,
            checkpoint=variants.checkpoint,
        )
        self.assertTrue(finished.done)

    async def test_rozetka_token_identity_and_full_scope(self) -> None:
        """Читает профиль, список и архив без фильтра наличия и обязательного rz_item_id."""
        http = PageHttp(
            [
                {"success": True, "content": {"market": {"id": 1086}, "id": 1}},
                fixture("rozetka-products.json"),
                fixture("rozetka-archive.json"),
            ]
        )
        platform = InstalledPlatforms(http).get("rozetka")
        validated = platform.validate(
            self.config("rozetka"), {"token": "private-token"}
        )
        self.assertEqual(
            (await platform.verify(validated.config, validated.credentials)).key, "1086"
        )
        self.assertEqual(http.calls[0][0], "GET")
        self.assertTrue(http.calls[0][1].endswith("/sites/get-auth-data"))
        self.assertNotIn("body", http.calls[0][2])
        page = await platform.read_publications(
            config=validated.config,
            credentials=validated.credentials,
            checkpoint=PublicationCheckpoint(),
        )
        self.assertFalse(page.done)
        self.assertEqual(page.items[0].external_id, "107:7372")
        self.assertIsNone(page.items[0].platform_data["rz_item_id"])
        self.assertNotIn("available", parse_qs(urlsplit(http.calls[1][1]).query))
        archive = await platform.read_publications(
            config=validated.config,
            credentials=validated.credentials,
            checkpoint=page.checkpoint,
        )
        self.assertTrue(archive.done)
        self.assertEqual(archive.items[0].external_id, page.items[0].external_id)
        self.assertEqual(urlsplit(http.calls[2][1]).path, "/goods/archive")
        self.assertNotIn("available", parse_qs(urlsplit(http.calls[2][1]).query))

    async def test_rozetka_resumed_pages_do_not_filter_availability(self) -> None:
        """Продолжение обоих потоков передаёт только параметры пагинации."""
        for stream in ("all", "archive"):
            with self.subTest(stream=stream):
                response = fixture("rozetka-products.json")
                response["content"]["_meta"] = {"currentPage": 2, "pageCount": 3}
                http = PageHttp([response])
                platform = InstalledPlatforms(http).get("rozetka")
                validated = platform.validate(
                    self.config("rozetka"), {"token": "private-token"}
                )
                page = await platform.read_publications(
                    config=validated.config,
                    credentials=validated.credentials,
                    checkpoint=PublicationCheckpoint(
                        cursor={"stream": stream, "page": 2}
                    ),
                )
                request = urlsplit(http.calls[0][1])
                self.assertEqual(request.path, "/goods/" + stream)
                self.assertEqual(
                    parse_qs(request.query),
                    {"page": ["2"], "pageSize": ["100"]},
                )
                self.assertFalse(page.done)
                self.assertEqual(page.checkpoint.cursor, {"stream": stream, "page": 3})
                self.assertEqual(page.items[0].data.availability, "removed")

    async def test_invalid_source_does_not_become_empty_success(self) -> None:
        """Не принимает отказ с HTTP 200 за пустой успешный обход."""
        platform = InstalledPlatforms(
            PageHttp([{"success": False, "errors": {"message": "invalid_credentials"}}])
        ).get("rozetka")
        validated = platform.validate(
            self.config("rozetka"), {"token": "private-token"}
        )
        with self.assertRaises(VerificationFailure) as error:
            await platform.read_publications(
                config=validated.config,
                credentials=validated.credentials,
                checkpoint=PublicationCheckpoint(),
            )
        self.assertEqual(error.exception.code, "invalid_credentials")

    async def test_prom_native_ua_and_missing_translation(self) -> None:
        """Код ua становится uk, а нелокализованное name не подменяет перевод."""
        http = PageHttp(
            [
                {
                    "products": [
                        {
                            "id": 1,
                            "name": "Нативное имя",
                            "name_multilang": {"ua": "Назва", "ru": "Название"},
                        },
                        {
                            "id": 2,
                            "name": "Русское имя",
                            "name_multilang": {"ru": "Русское имя"},
                        },
                    ]
                }
            ]
        )
        platform = InstalledPlatforms(http).get("prom")
        validated = platform.validate(self.config("prom"), {"token": "fixture-token"})
        page = await platform.read_publications(
            config=validated.config,
            credentials=validated.credentials,
            checkpoint=PublicationCheckpoint(),
        )
        self.assertEqual(page.items[0].data.titles[0], PublicationTitle("uk", "Назва"))
        self.assertIsNone(page.items[1].data.titles[0].title)

    async def test_unsupported_woo_extension_does_not_require_supported_shape(
        self,
    ) -> None:
        """Нативные поля неизвестного типа не валидируются как поддержанный товар."""
        http = PageHttp(
            [{}, [{"id": 777, "type": "custom_bundle", "price": {"custom": True}}]]
        )
        platform = InstalledPlatforms(http).get("woocommerce")
        validated = platform.validate(
            self.config("woocommerce"),
            {"consumer_key": "ck-test", "consumer_secret": "cs-test"},
        )
        page = await platform.read_publications(
            config=validated.config,
            credentials=validated.credentials,
            checkpoint=PublicationCheckpoint(),
        )
        self.assertEqual(
            (page.processed_count, page.skipped_count, len(page.items)), (1, 1, 0)
        )
