"""Форматы, точность, безопасная сеть и жизненный цикл импорта Catalog."""

import asyncio
import io
import ipaddress
import unittest
from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, patch
from uuid import uuid4
from src.modules.catalog.domain.catalog_import.aggregate import CatalogImport
from src.modules.catalog.domain.catalog_import.value_object.configuration import (
    ImportConfiguration,
    ImportFieldMapping,
)
from src.modules.catalog.domain.error import (
    CatalogConflictError,
    InvalidCatalogValueError,
)
from src.modules.catalog.infrastructure.catalog_import.parser import CatalogImportParser
from src.modules.catalog.infrastructure.catalog_import.download import (
    PublicNetworkBackend,
    validate_public_url,
    public_address,
)
from src.modules.catalog.application.catalog_import.auto_mapping import suggest_mappings
from src.modules.catalog.application.catalog_import.values import (
    mapped_values,
    product_values,
    image_urls,
    date_value,
)
from src.modules.catalog.domain.catalog_item.aggregate import CatalogItem
from src.modules.catalog.domain.catalog_item.value_object.identifier import (
    CatalogItemIdVO,
)
from src.modules.catalog.domain.catalog_item.value_object.price import (
    PriceSpecificationVO,
)
from src.modules.catalog.domain.catalog_item.value_object.measurements import (
    DimensionsVO,
    LengthVO,
    LengthUnit,
)
from src.modules.catalog.presentation.catalog_import.http.controller.export_catalog_import_report import (
    report_cell,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


class CatalogImportParserTests(unittest.TestCase):
    """Проверяет реальные особенности экспорта и ограничение памяти одной записью."""

    def test_prom_csv_duplicate_columns_short_rows_decimal_and_two_languages(
        self,
    ) -> None:
        data = (
            "Код_товару,Назва_позиції,Назва_позиції_укр,Ціна,Валюта,Кількість,Назва_Характеристики,Назва_Характеристики\n"
            'SKU-1,Название,Назва,"507,7",UAH,2,Первая,Вторая\n'
            "SKU-2,Другая,Інша,0,UAH,0\n"
        ).encode("utf-8-sig")
        source = io.BytesIO(data)
        parser = CatalogImportParser(100)
        description = parser.inspect(source, ImportConfiguration())
        rows = list(parser.records(source, description))
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0].values["c:6"], ["Первая"])
        self.assertEqual(rows[0].values["c:7"], ["Вторая"])
        self.assertEqual(rows[1].values["c:7"], [""])
        configuration = ImportConfiguration(
            mappings=suggest_mappings(description.fields, "uk")
        )
        product = product_values(
            configuration, mapped_values(configuration, rows[0].values)
        ).product
        self.assertEqual(product.price_specification.regular_price, Decimal("507.7"))
        self.assertEqual(set(product.translations), {"ru", "uk"})
        self.assertTrue(product.stock.manage_stock)
        self.assertEqual(product.stock.stock_quantity, 2)
        self.assertIsNone(
            product_values(
                configuration, mapped_values(configuration, rows[1].values)
            ).product.weight
        )
        self.assertFalse(source.closed)

    def test_csv_quoted_multiline_cp1251_semicolon_and_tab(self) -> None:
        for delimiter in [";", "\t"]:
            with self.subTest(delimiter=delimiter):
                data = f'sku{delimiter}title{delimiter}body\n1{delimiter}Название{delimiter}"строка 1\nстрока 2"\n'.encode(
                    "cp1251"
                )
                source = io.BytesIO(data)
                parser = CatalogImportParser(5)
                description = parser.inspect(source, ImportConfiguration())
                self.assertEqual(description.encoding, "cp1251")
                self.assertEqual(description.delimiter, delimiter)
                self.assertEqual(
                    next(parser.records(source, description)).values["c:2"],
                    ["строка 1\nстрока 2"],
                )

    def test_prom_xml_repeated_images_cdata_and_attributes(self) -> None:
        source = io.BytesIO(b"""<?xml version="1.0"?><yml_catalog><shop><offers>
          <offer id="external" available="true"><vendorCode>A</vendorCode><name>Title</name><name_ua>UK</name_ua>
          <description><![CDATA[<p>Hello &amp; world</p>]]></description><picture>https://example.com/1.png</picture><picture>https://example.com/2.png</picture></offer>
          <offer id="second"><vendorCode>B</vendorCode><name>Second</name></offer>
        </offers></shop></yml_catalog>""")
        parser = CatalogImportParser(10)
        description = parser.inspect(source, ImportConfiguration())
        self.assertEqual(description.record_path, "/yml_catalog/shop/offers/offer")
        rows = list(parser.records(source, description))
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0].values["@id"], ["external"])
        self.assertEqual(len(rows[0].values["picture"]), 2)
        self.assertEqual(rows[0].values["description"], ["<p>Hello &amp; world</p>"])

    def test_arbitrary_xml_namespaces_and_explicit_candidate(self) -> None:
        source = io.BytesIO(
            b'<feed xmlns:p="urn:products"><p:entry><p:sku>A</p:sku><p:nested><p:title>One</p:title></p:nested></p:entry><p:entry><p:sku>B</p:sku></p:entry></feed>'
        )
        parser = CatalogImportParser(10)
        path = "/feed/{urn:products}entry"
        description = parser.inspect(source, ImportConfiguration(record_path=path))
        rows = list(parser.records(source, description))
        self.assertEqual(
            rows[0].values["{urn:products}nested/{urn:products}title"], ["One"]
        )
        self.assertEqual(rows[1].values["{urn:products}sku"], ["B"])
        with self.assertRaises(InvalidCatalogValueError):
            parser.inspect(source, ImportConfiguration(record_path="/feed/missing"))

    def test_invalid_xml_entities_depth_and_record_limits(self) -> None:
        parser = CatalogImportParser(1)
        for raw in [
            b'<!DOCTYPE x [<!ENTITY y SYSTEM "file:///etc/passwd">]><x>&y;</x>',
            b"<x><broken></x>",
            b"<x>" * 66 + b"</x>" * 66,
        ]:
            with (
                self.subTest(raw=raw[:40]),
                self.assertRaises(InvalidCatalogValueError),
            ):
                parser.inspect(io.BytesIO(raw), ImportConfiguration())
        source = io.BytesIO(b"sku,title\n1,One\n2,Two\n")
        description = parser.inspect(source, ImportConfiguration())
        with self.assertRaises(InvalidCatalogValueError):
            list(parser.records(source, description))

    def test_xml_records_can_contain_only_attributes_or_text(self) -> None:
        parser = CatalogImportParser(10)
        for raw, expected in [
            (
                b'<feed><item sku="A"/><item sku="B"/></feed>',
                {"@sku": ["A"], ".": [""]},
            ),
            (b"<feed><item>A</item><item>B</item></feed>", {".": ["A"]}),
        ]:
            with self.subTest(raw=raw):
                source = io.BytesIO(raw)
                description = parser.inspect(source, ImportConfiguration())
                self.assertEqual(description.record_path, "/feed/item")
                rows = list(parser.records(source, description))
                self.assertEqual(len(rows), 2)
                self.assertEqual(rows[0].values, expected)

    def test_xml_candidate_paths_are_bounded(self) -> None:
        source = io.BytesIO(
            (
                "<feed>" + "".join(f"<field{i}/>" for i in range(2001)) + "</feed>"
            ).encode()
        )
        with self.assertRaises(InvalidCatalogValueError):
            CatalogImportParser(10).inspect(source, ImportConfiguration())

    def test_standard_yml_doctype_is_inert_but_internal_subset_is_forbidden(
        self,
    ) -> None:
        parser = CatalogImportParser(10)
        source = io.BytesIO(
            b'<!DOCTYPE yml_catalog SYSTEM "shops.dtd"><yml_catalog><shop><offers><offer><name>One</name></offer></offers></shop></yml_catalog>'
        )
        description = parser.inspect(source, ImportConfiguration())
        self.assertEqual(len(list(parser.records(source, description))), 1)
        for declaration in [
            b'<!DOCTYPE yml_catalog SYSTEM "https://example.com/shops.dtd">',
            b'<!DOCTYPE yml_catalog SYSTEM "shops.dtd" [<!ENTITY x "bad">]>',
        ]:
            with self.assertRaises(InvalidCatalogValueError):
                parser.inspect(
                    io.BytesIO(declaration + b"<yml_catalog/>"), ImportConfiguration()
                )


class CatalogImportValuesTests(unittest.TestCase):
    """Сохраняет точность и семантику частичного обновления."""

    def setUp(self) -> None:
        self.configuration = ImportConfiguration()
        self.now = datetime.now(UTC)
        self.actor = EntityIdVO(uuid4())
        self.item = CatalogItem.create(
            CatalogItemIdVO(uuid4()), self.actor, self.now, EntityIdVO(uuid4())
        )
        self.item.update(
            fields=frozenset({"price_specification", "dimensions"}),
            actor=self.actor,
            now=self.now,
            price_specification=PriceSpecificationVO(
                Decimal("100"), "UAH", Decimal("90")
            ),
            dimensions=DimensionsVO(length=LengthVO(Decimal("5"), LengthUnit.CM)),
        )

    def test_partial_price_and_dimension_updates_preserve_other_fields(self) -> None:
        result = product_values(
            self.configuration,
            {"sale_price": ["85,50"], "width": ["2"], "width_unit": ["cm"]},
            self.item,
        )
        self.assertEqual(
            result.product.price_specification.regular_price, Decimal("100")
        )
        self.assertEqual(
            result.product.price_specification.sale_price, Decimal("85.50")
        )
        self.assertEqual(result.product.dimensions.length.value, Decimal("5"))
        self.assertEqual(result.product.dimensions.width.value, Decimal("2"))

    def test_empty_absent_zero_and_false_are_distinct(self) -> None:
        config = ImportConfiguration(
            mappings=(
                ImportFieldMapping("regular_price", "price"),
                ImportFieldMapping("virtual", "virtual"),
            )
        )
        values = mapped_values(config, {"price": ["0"], "virtual": ["false"]})
        self.assertEqual(values, {"regular_price": ["0"], "virtual": ["false"]})
        self.assertEqual(mapped_values(config, {"price": [""]}), {})
        clearing = replace(config, clear_empty=True)
        self.assertEqual(
            mapped_values(clearing, {"price": [""]}), {"regular_price": [""]}
        )
        self.assertIsNone(
            product_values(
                clearing, {"regular_price": [""]}, self.item
            ).product.price_specification
        )

    def test_discount_exact_no_rounding_and_fractional_stock_rejected(self) -> None:
        with self.assertRaises(InvalidCatalogValueError):
            product_values(
                self.configuration,
                {
                    "regular_price": ["100.123456"],
                    "currency": ["UAH"],
                    "discount": ["10%"],
                },
            )
        self.assertEqual(
            product_values(
                self.configuration,
                {"regular_price": ["100"], "currency": ["UAH"], "discount": ["10%"]},
            ).product.price_specification.sale_price,
            Decimal(90),
        )

    def test_prom_stock_and_services(self) -> None:
        product = product_values(
            self.configuration,
            {"stock_quantity": ["0"], "stock_status": ["+"], "virtual": ["s"]},
        ).product
        self.assertEqual(product.stock.effective_status().value, "out_of_stock")
        self.assertTrue(product.virtual)
        self.assertEqual(
            product_values(
                self.configuration, {"stock_status": ["9"]}
            ).product.stock.stock_status.value,
            "on_backorder",
        )
        with self.assertRaises(InvalidCatalogValueError):
            product_values(self.configuration, {"stock_quantity": ["1.1"]})
        with self.assertRaises(InvalidCatalogValueError):
            product_values(self.configuration, {"stock_status": ["mystery"]})

    def test_dates_timezone_interval_and_ambiguous_time(self) -> None:
        self.assertEqual(
            date_value("25.10.2026", "Europe/Kyiv", True),
            datetime(2026, 10, 25, 22, tzinfo=UTC),
        )
        self.assertEqual(
            date_value("2026-01-01T12:30:00Z", "Europe/Warsaw"),
            datetime(2026, 1, 1, 12, 30, tzinfo=UTC),
        )
        with self.assertRaises(InvalidCatalogValueError):
            date_value("2026-10-25T03:30:00", "Europe/Kyiv")

    def test_image_url_arrays_order_and_formula_protection(self) -> None:
        self.assertEqual(
            image_urls(
                [
                    "https://example.com/1.png, https://example.com/2.png",
                    "https://example.com/1.png",
                ]
            ),
            ("https://example.com/1.png", "https://example.com/2.png"),
        )
        self.assertEqual(
            image_urls(['["https://example.com/1.png"]']),
            ("https://example.com/1.png",),
        )
        for value in [
            '=HYPERLINK("bad")',
            "+formula",
            "-formula",
            "@formula",
            "\tformula",
        ]:
            self.assertTrue(report_cell(value).startswith("'"))


class CatalogImportLifecycleTests(unittest.TestCase):
    """Проверяет переходы, повтор старта и монотонные счётчики."""

    def test_start_configure_version_cancel_and_counters(self) -> None:
        now = datetime.now(UTC)
        configuration = ImportConfiguration(
            mappings=(ImportFieldMapping("sku", "c:0"),)
        )
        entity = CatalogImport.create(
            identifier=EntityIdVO(uuid4()),
            actor_id=EntityIdVO(uuid4()),
            key="test",
            fingerprint="f" * 64,
            name="test.csv",
            url=None,
            file_id=EntityIdVO(uuid4()),
            configuration=configuration,
            now=now,
        )
        with self.assertRaises(CatalogConflictError):
            entity.start(1, now)
        entity.prepared(2, now)
        with self.assertRaises(CatalogConflictError):
            entity.start(2, now)
        self.assertTrue(entity.start(1, now))
        self.assertFalse(entity.start(1, now))
        with self.assertRaises(CatalogConflictError):
            entity.configure(configuration, now)
        entity.begin(now)
        entity.record("created", 1, now)
        self.assertEqual((entity.processed, entity.created, entity.warnings), (1, 1, 1))
        entity.cancel(now)
        self.assertEqual(entity.status, "cancelling")
        entity.stop(now)
        self.assertEqual(entity.status, "cancelled")
        self.assertEqual(entity.processed, 1)

    def test_required_sku_mapping_and_duplicate_target_rejected(self) -> None:
        with self.assertRaises(InvalidCatalogValueError):
            ImportConfiguration(mode="update").ensure_startable()
        with self.assertRaises(InvalidCatalogValueError):
            ImportConfiguration(
                mappings=(
                    ImportFieldMapping("sku", "c:0"),
                    ImportFieldMapping("sku", "c:1"),
                )
            )


class CatalogImportNetworkTests(unittest.IsolatedAsyncioTestCase):
    """Проверяет SSRF до connect и pinning разрешённого адреса."""

    async def test_private_addresses_credentials_ports_and_dns_rebinding(self) -> None:
        for url in [
            "file:///etc/passwd",
            "http://127.0.0.1/x",
            "http://169.254.169.254/",
            "http://[::1]/",
            "https://u:p@example.com/",
            "https://example.com:8000/",
            "http://localhost/",
        ]:
            with self.subTest(url=url), self.assertRaises(InvalidCatalogValueError):
                validate_public_url(url)
        self.assertFalse(public_address(ipaddress.ip_address("::ffff:127.0.0.1")))
        loop = asyncio.get_running_loop()
        with patch.object(
            loop,
            "getaddrinfo",
            AsyncMock(return_value=[(2, 1, 6, "", ("127.0.0.1", 443))]),
        ):
            with self.assertRaises(InvalidCatalogValueError):
                await PublicNetworkBackend().connect_tcp("example.com", 443)
        with (
            patch.object(
                loop,
                "getaddrinfo",
                AsyncMock(return_value=[(2, 1, 6, "", ("93.184.216.34", 443))]),
            ),
            patch(
                "httpcore.AnyIOBackend.connect_tcp", AsyncMock(return_value="stream")
            ) as connect,
        ):
            self.assertEqual(
                await PublicNetworkBackend().connect_tcp("example.com", 443), "stream"
            )
            self.assertEqual(connect.call_args.args[0], "93.184.216.34")


class CatalogImportContractsTests(unittest.IsolatedAsyncioTestCase):
    """Проверяет HTTP-документацию, лимиты и отсутствие сети при прикреплении файлов."""

    def test_openapi_both_sources_and_default_limits(self) -> None:
        from fastapi import FastAPI
        from src.config.feature.catalog_import_config import CatalogImportSettings
        from src.modules.catalog.presentation.catalog_import.router import router

        app = FastAPI()
        app.include_router(router, prefix="/api/console")
        schema = app.openapi()
        content = schema["paths"]["/api/console/catalog/imports"]["post"][
            "requestBody"
        ]["content"]
        self.assertEqual(set(content), {"application/json", "multipart/form-data"})
        self.assertEqual(content["application/json"]["schema"]["required"], ["url"])
        self.assertEqual(content["multipart/form-data"]["schema"]["required"], ["file"])
        settings = CatalogImportSettings()
        self.assertEqual(settings.max_records, 100000)
        self.assertEqual(settings.source_max_bytes, 100 * 1024 * 1024)
        self.assertEqual(settings.download_concurrency, 4)
        self.assertEqual(settings.max_images, 100)
        self.assertEqual(settings.image_max_bytes, 10 * 1024 * 1024)
        self.assertEqual((settings.batch_size, settings.batch_seconds), (100, 60))
        self.assertEqual(
            (settings.draft_hours, settings.source_days, settings.result_days),
            (24, 7, 30),
        )
        with self.assertRaises(ValueError):
            CatalogImportSettings(source_days=31, result_days=30)

    async def test_prepared_image_attachment_uses_only_sql_metadata(self) -> None:
        from types import SimpleNamespace
        from src.modules.catalog.infrastructure.catalog_import.files import (
            FilesCatalogImportImages,
        )

        delegate, ready, artifacts = AsyncMock(), AsyncMock(), AsyncMock()
        artifacts.location.return_value = SimpleNamespace(content_type="image/png")
        adapter = FilesCatalogImportImages(delegate, ready, artifacts)
        tenant, file_id = uuid4(), uuid4()
        await adapter.ensure_images(tenant, (file_id, file_id))
        ready.execute.assert_awaited_once()
        artifacts.location.assert_awaited_once_with(tenant, file_id)
        delegate.content.assert_not_awaited()
        artifacts.location.return_value = SimpleNamespace(content_type="text/html")
        with self.assertRaises(InvalidCatalogValueError):
            await adapter.ensure_images(tenant, (file_id,))

    async def test_cancelled_parser_finishes_before_resource_is_closed(self) -> None:
        import threading
        from src.modules.catalog.presentation.catalog_import.jobs import run_parser

        started, release, finished = (
            threading.Event(),
            threading.Event(),
            threading.Event(),
        )

        def action():
            started.set()
            release.wait(timeout=2)
            finished.set()
            return 1

        task = asyncio.create_task(run_parser(action))
        await asyncio.to_thread(started.wait, 2)
        task.cancel()
        release.set()
        with self.assertRaises(asyncio.CancelledError):
            await task
        self.assertTrue(finished.is_set())


class CatalogImportAnalysisTests(unittest.TestCase):
    """Предложения и предупреждения формируются во внутреннем Application-сервисе."""

    def test_analysis_preserves_duplicate_source_ids_and_reports_stock_conflict(
        self,
    ) -> None:
        from src.modules.catalog.application.catalog_import.analysis_service import (
            build_import_analysis,
        )
        from src.modules.catalog.application.catalog_import.contracts import (
            SourceField,
            SourceRecord,
            SourceDescription,
        )

        fields = (
            SourceField("c:0", "sku"),
            SourceField("c:1", "stock_quantity"),
            SourceField("c:2", "stock_status"),
        )
        description = SourceDescription("csv", "utf-8-sig", ",", None, (), fields)
        config, analysis = build_import_analysis(
            description,
            fields,
            (SourceRecord(1, {"c:0": ["A"], "c:1": ["0"], "c:2": ["+"]}),),
            ImportConfiguration(),
        )
        self.assertEqual(len(config.mappings), 3)
        self.assertEqual(len(analysis.warnings), 1)
        self.assertEqual(analysis.fields[1].id, "c:1")
        with self.assertRaises(InvalidCatalogValueError):
            build_import_analysis(
                description,
                fields,
                (),
                ImportConfiguration(mappings=(ImportFieldMapping("sku", "missing"),)),
            )

    def test_nonlocalized_fields_cannot_be_duplicated_using_locale(self) -> None:
        with self.assertRaises(InvalidCatalogValueError):
            ImportFieldMapping("regular_price", "c:1", locale="ru")
        with self.assertRaises(InvalidCatalogValueError):
            ImportConfiguration(
                mappings=(
                    ImportFieldMapping("images", "c:1"),
                    ImportFieldMapping("images", "c:2", locale="ru"),
                )
            )

    def test_yml_oldprice_precedence_and_image_text_arrays(self) -> None:
        from src.modules.catalog.application.catalog_import.contracts import SourceField
        from src.modules.catalog.application.catalog_import.values import image_texts

        fields = (
            SourceField("old", "oldprice"),
            SourceField("alias", "price_old"),
            SourceField("sale", "price"),
            SourceField("discount", "discount"),
        )
        mappings = {
            mapping.target: mapping.source for mapping in suggest_mappings(fields, "uk")
        }
        self.assertEqual(mappings["regular_price"], "old")
        self.assertEqual(mappings["sale_price"], "sale")
        self.assertNotIn("discount", mappings)
        self.assertEqual(image_texts(['["One", "Two"]']), ["One", "Two"])
        self.assertEqual(image_texts(["[literal]"]), ["[literal]"])


class CatalogImportDownloadTests(unittest.IsolatedAsyncioTestCase):
    """Проверяет redirect и реальный размер, не доверяя HTTP-заголовкам."""

    async def test_private_redirect_and_declared_length_cannot_bypass_limits(
        self,
    ) -> None:
        from src.modules.catalog.infrastructure.catalog_import.download import (
            download_public_file,
        )

        class Response:
            def __init__(self, status, headers, chunks):
                self.status, self.headers, self.chunks = status, headers, chunks

            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                return None

            async def aiter_stream(self):
                for chunk in self.chunks:
                    yield chunk

        class Pool:
            def __init__(self, response):
                self.response, self.calls = response, 0

            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                return None

            def stream(self, *args, **kwargs):
                self.calls += 1
                return self.response

        pool = Pool(Response(302, [(b"location", b"http://127.0.0.1/private")], []))
        with patch("httpcore.AsyncConnectionPool", return_value=pool):
            with self.assertRaises(InvalidCatalogValueError):
                await download_public_file("https://example.com/source.csv", 10, 1)
        self.assertEqual(pool.calls, 1)
        pool = Pool(Response(200, [(b"content-length", b"1")], [b"1234", b"5678"]))
        with patch("httpcore.AsyncConnectionPool", return_value=pool):
            with self.assertRaises(InvalidCatalogValueError):
                await download_public_file("https://example.com/source.csv", 4, 1)

    def test_iri_path_is_encoded_without_disabling_tls_or_allowing_credentials(
        self,
    ) -> None:
        url = validate_public_url("https://example.com/фото 1.png?q=опис")
        self.assertTrue(url.isascii())
        self.assertIn("%20", url)
        with self.assertRaises(InvalidCatalogValueError):
            validate_public_url("https://@example.com/")
