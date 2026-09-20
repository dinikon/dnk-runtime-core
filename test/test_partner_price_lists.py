from __future__ import annotations
import asyncio
import os
import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path
from decimal import Decimal
from uuid import UUID, uuid4
from unittest.mock import AsyncMock, Mock, patch
from contextlib import aclosing
from openpyxl import Workbook
from cryptography.fernet import Fernet
from src.modules.price_lists.domain import (
    canonical_state_hash,
    normalize_availability,
    mask_source_url,
    MappingValidationError,
)
from src.modules.price_lists.application.sync_run.job_identity import (
    deterministic_job_id,
    deterministic_cleanup_job_id,
)
from src.modules.price_lists.infrastructure.source import (
    SourceParser,
    SourceUrlCipher,
    HttpRemoteFileFetcher,
    prom_xml_config,
)
from src.modules.price_lists.infrastructure.calendar import CronCalendar
from src.modules.price_lists.domain.price_list.error import (
    PriceListValidationError,
    PriceListStateConflict,
)
from src.modules.price_lists.domain.offer.error import InvalidOfferValueError
from src.modules.price_lists.domain.offer.value_object.money import MoneyVO, QuantityVO
from src.modules.price_lists.application.sync_run.options import ImportOptions
from src.modules.price_lists.domain.sync_run.entity import SyncRun
from src.modules.price_lists.domain.sync_run.error import SourceValidationError
from src.modules.price_lists.domain.price_list.entity import PriceList
from src.modules.price_lists.domain.price_list.value_object import PriceListIdVO
from src.modules.price_lists.domain.price_list.value_object.configuration import (
    ScheduleVO,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


class PartnerPriceListDomainTests(unittest.TestCase):
    def test_metrics_state_hash_and_secret_masking(self) -> None:
        state_hash = canonical_state_hash(
            purchase_price=Decimal("80.00"),
            rrp=Decimal("100.00"),
            currency="uah",
            availability="in_stock",
            quantity=3,
        )
        self.assertEqual(len(state_hash), 64)
        self.assertEqual(normalize_availability("В наличии"), "in_stock")
        self.assertEqual(normalize_availability("В наличии", 0), "out_of_stock")
        self.assertEqual(
            mask_source_url(
                "https://partner.example/private/token/file.xlsx?key=secret"
            ),
            "https://partner.example/…/file.xlsx",
        )

    def test_deterministic_job_id_and_timezone_cron(self) -> None:
        tenant_id = UUID("11111111-1111-1111-1111-111111111111")
        price_list_id = UUID("22222222-2222-2222-2222-222222222222")
        first = deterministic_job_id(
            tenant_id, price_list_id, 3, "2026-09-18T12:00:00Z"
        )
        second = deterministic_job_id(
            tenant_id, price_list_id, 3, "2026-09-18T12:00:00Z"
        )
        self.assertEqual(first, second)
        self.assertEqual(
            deterministic_cleanup_job_id(tenant_id, "2026-09-19T03:00:00+00:00"),
            deterministic_cleanup_job_id(tenant_id, "2026-09-19T03:00:00+00:00"),
        )
        next_at = CronCalendar().next(
            "0 9 * * *",
            "Europe/Kyiv",
            after=datetime(2026, 1, 1, 7, 30, tzinfo=UTC),
        )
        self.assertEqual(next_at, datetime(2026, 1, 2, 7, 0, tzinfo=UTC))

    def test_source_url_is_encrypted_and_fast_cron_is_rejected(self) -> None:
        cipher = SourceUrlCipher(Fernet.generate_key().decode("ascii"))
        source = "https://partner.example/private/token.xlsx?key=secret"
        encrypted = cipher.encrypt(source)
        self.assertNotIn("secret", encrypted)
        self.assertEqual(cipher.decrypt(encrypted), source)
        with self.assertRaisesRegex(PriceListValidationError, "at least 15 minutes"):
            CronCalendar().occurrences(
                "*/5 * * * *", "Europe/Kyiv", after=datetime.now(UTC)
            )


class PartnerPriceListParserTests(unittest.TestCase):
    def setUp(self) -> None:
        self.parser = SourceParser()

    def test_prom_xml_preset_parses_attributes_and_prices(self) -> None:
        source, mapping = prom_xml_config()
        xml = b"""<?xml version='1.0'?>
        <!DOCTYPE yml_catalog SYSTEM 'shops.dtd'>
        <yml_catalog><shop><offers>
          <offer id='42' available='true'><vendorCode>SKU-42</vendorCode>
          <name>Protein</name><price>120.50</price><priceRRP>180</priceRRP>
          <currencyId>UAH</currencyId></offer>
        </offers></shop></yml_catalog>"""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sample.xml"
            path.write_bytes(xml)
            row = next(self.parser.rows(path, "xml", source, mapping))
        self.assertFalse(row.errors)
        self.assertEqual(row.normalized["external_id"], "42")
        self.assertEqual(row.normalized["purchase_price"], Decimal("120.50"))
        self.assertEqual(row.normalized["availability"], "in_stock")

    def test_prom_xml_available_semantics(self) -> None:
        source, mapping = prom_xml_config()
        cases = [
            ("склад", "in_stock"),
            ("true", "in_stock"),
            ("false", "out_of_stock"),
            ("", "out_of_stock"),
            ("   ", "out_of_stock"),
            (None, "out_of_stock"),
            (" СКЛАД ", "in_stock"),
        ]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sample.xml"
            for available, expected in cases:
                with self.subTest(available=available):
                    attribute = (
                        f'available="{available}"' if available is not None else ""
                    )
                    legacy = "false" if expected == "in_stock" else "true"
                    path.write_text(
                        f"""<yml_catalog><shop><offers>
                        <offer id="42" {attribute} in_stock="{legacy}">
                        <vendorCode>SKU</vendorCode><name>Item</name><price>10</price>
                        </offer></offers></shop></yml_catalog>""",
                        encoding="utf-8",
                    )
                    row = next(self.parser.rows(path, "xml", source, mapping))
                    self.assertFalse(row.errors)
                    self.assertEqual(row.normalized["availability"], expected)

    def test_xml_parser_matches_the_full_configured_item_path(self) -> None:
        source, mapping = prom_xml_config()
        xml = b"""<yml_catalog><metadata><offer id='wrong'/></metadata><shop>
        <offers><offer id='right' available='false'><vendorCode>SKU</vendorCode>
        <name>Item</name><price>10</price><currencyId>UAH</currencyId>
        </offer></offers></shop></yml_catalog>"""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sample.xml"
            path.write_bytes(xml)
            rows = list(self.parser.rows(path, "xml", source, mapping))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].normalized["external_id"], "right")

    def test_extensionless_xlsx_is_read_only_and_uses_header_mapping(self) -> None:
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "Sheet1"
        sheet.append(
            [
                "Артикул",
                "Название (UA)",
                "РРЦ",
                "Цена",
                "Валюта",
                "Наличие",
                "Количество",
            ]
        )
        sheet.append(["SKU-1", "Товар", 150, 100, "UAH", "В наличии", 4])
        mapping = {
            "external_id": {"selector": "Артикул", "required": True},
            "sku": {"selector": "Артикул", "required": True},
            "title": {"selector": "Название (UA)", "required": True},
            "purchase_price": {"selector": "Цена", "required": True},
            "rrp": {"selector": "РРЦ"},
            "currency": {"selector": "Валюта", "required": True},
            "availability": {"selector": "Наличие"},
            "quantity": {"selector": "Количество"},
        }
        with tempfile.TemporaryDirectory() as directory:
            # HttpRemoteFileFetcher uses an extensionless random temporary path.
            path = Path(directory) / "downloaded-price-list"
            workbook.save(path)
            inspection = self.parser.inspect(
                path, "xlsx", {"sheet_name": "Sheet1", "header_row": 1}
            )
            row = next(
                self.parser.rows(
                    path,
                    "xlsx",
                    {"sheet_name": "Sheet1", "header_row": 1, "data_start_row": 2},
                    mapping,
                )
            )
        self.assertIn("Цена", inspection["columns"])
        self.assertEqual(row.normalized["quantity"], 4)
        self.assertEqual(row.normalized["availability"], "in_stock")

    def test_unsafe_xml_entities_and_broken_xlsx_are_rejected(self) -> None:
        source, mapping = prom_xml_config()
        entity_xml = b"""<?xml version='1.0'?><!DOCTYPE x [<!ENTITY e 'secret'>]>
        <yml_catalog><shop><offers><offer id='1'><vendorCode>A</vendorCode>
        <name>&e;</name><price>1</price><currencyId>UAH</currencyId>
        </offer></offers></shop></yml_catalog>"""
        with tempfile.TemporaryDirectory() as directory:
            xml_path = Path(directory) / "entity.xml"
            xml_path.write_bytes(entity_xml)
            with self.assertRaises(Exception):
                list(self.parser.rows(xml_path, "xml", source, mapping))
            xlsx_path = Path(directory) / "broken.xlsx"
            xlsx_path.write_bytes(b"not-a-zip")
            with self.assertRaises(MappingValidationError):
                self.parser.inspect(xlsx_path, "xlsx", {})


class PartnerPriceListFetcherTests(unittest.IsolatedAsyncioTestCase):
    async def test_fetcher_rejects_credentials_and_private_networks(self) -> None:
        fetcher = HttpRemoteFileFetcher()
        with self.assertRaisesRegex(PriceListValidationError, "credentials"):
            await fetcher._validate_url("https://user:password@example.com/file.xml")
        with self.assertRaisesRegex(PriceListValidationError, "non-public"):
            await fetcher._validate_url("https://127.0.0.1/file.xml")


class PriceListValueTests(unittest.TestCase):
    def test_money_normalization_and_invalid_values(self):
        self.assertEqual(MoneyVO("10").value, MoneyVO("10.0000").value)
        self.assertEqual(MoneyVO("1.23455").value, Decimal("1.2346"))
        for value in (
            "NaN",
            "sNaN",
            "Infinity",
            "-Infinity",
            "-1",
            "1000000000000000",
            "999999999999999.99999",
        ):
            with self.subTest(value=value), self.assertRaises(InvalidOfferValueError):
                MoneyVO(value)
        for value in ("1.9", "NaN", "Infinity", "2147483648", -1):
            with self.subTest(value=value), self.assertRaises(InvalidOfferValueError):
                QuantityVO(value)
        self.assertEqual(QuantityVO("1.000").value, 1)

    def test_equal_numeric_values_produce_same_hash(self):
        base = dict(rrp=None, currency="UAH", availability="in_stock", quantity=1)
        self.assertEqual(
            canonical_state_hash(purchase_price=Decimal("10"), **base),
            canonical_state_hash(purchase_price=Decimal("10.0000"), **base),
        )

    def test_inclusive_error_ratio_and_empty_source(self):
        run = Mock(counters={"read": 2, "rejected": 1})
        SyncRun.validate(run, 0.5)
        for counters in (
            {"read": 0, "rejected": 0},
            {"read": 2, "rejected": 2},
            {"read": 3, "rejected": 2},
        ):
            run.counters = counters
            with self.assertRaises(SourceValidationError):
                SyncRun.validate(run, 0.5)

    def test_entity_noop_and_paused_schedule(self):
        now = datetime.now(UTC)
        actor = EntityIdVO(uuid4())
        source, mapping = prom_xml_config()
        price = PriceList.create(
            price_list_id=PriceListIdVO(uuid4()),
            actor_id=actor,
            title=" Test ",
            source_format="xml",
            source_preset="prom_xml",
            source_url_secret="encrypted",
            source_url_display="masked",
            source_config=source,
            mapping_config=mapping,
            now=now,
        )
        self.assertEqual(price.title, "Test")
        self.assertEqual(price.created_at, price.updated_at)
        self.assertFalse(
            price.update({"title": "Test"}, actor, now + timedelta(hours=1))
        )
        self.assertEqual(price.updated_at, now)
        price.status = "paused"
        price.configure_schedule(
            ScheduleVO("0 */6 * * *", "Europe/Kyiv"),
            now + timedelta(hours=6),
            actor,
            now,
        )
        self.assertIsNone(price.next_sync_at)
        price.status = "active"
        with self.assertRaises(PriceListStateConflict):
            price.require_editable()


class StreamingParserTests(unittest.IsolatedAsyncioTestCase):
    def mapping(self):
        return {
            key: (
                {"selector": key, "constant": "UAH"}
                if key == "currency"
                else {"selector": key}
            )
            for key in ("external_id", "sku", "title", "purchase_price", "currency")
        }

    async def test_yaml_events_nested_selection_and_aliases(self):
        text = "defaults: &title Example\nshop:\n  offers:\n    - external_id: 1\n      sku: A\n      title: *title\n      purchase_price: 10\n    - external_id: 2\n      sku: B\n      title: Item\n      purchase_price: 11\n"
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "file"
            path.write_text(text)
            parser = SourceParser(ImportOptions(batch_size=1))
            rows = []
            async with aclosing(
                parser.batches(
                    path, "yaml", {"item_path": "shop.offers"}, self.mapping()
                )
            ) as batches:
                async for batch in batches:
                    self.assertEqual(len(batch), 1)
                    rows.extend(batch)
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[0].normalized["title"], "Example")
            self.assertTrue(all(not row.errors for row in rows))

    async def test_cancel_closes_producer_even_when_queue_is_full(self):
        source, mapping = prom_xml_config()
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "file"
            path.write_text(
                "<yml_catalog><shop><offers>"
                + "".join(
                    f'<offer id="{i}"><vendorCode>A</vendorCode><name>Item</name><price>1</price></offer>'
                    for i in range(10000)
                )
                + "</offers></shop></yml_catalog>"
            )
            parser = SourceParser(ImportOptions(batch_size=1, parser_queue_batches=1))
            stream = parser.batches(path, "xml", source, mapping)
            await anext(stream)
            await asyncio.sleep(0.05)
            await asyncio.wait_for(stream.aclose(), 2)

    async def test_malformed_tail_is_not_silently_accepted(self):
        source, mapping = prom_xml_config()
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "file"
            path.write_text(
                '<yml_catalog><shop><offers><offer id="1"><vendorCode>A</vendorCode><name>A</name><price>1</price></offer></wrong>'
            )
            with self.assertRaises(MappingValidationError):
                async with aclosing(
                    SourceParser().batches(path, "xml", source, mapping)
                ) as stream:
                    async for batch in stream:
                        pass

    async def test_record_and_row_limits_and_byte_batched_requests(self):
        source, mapping = prom_xml_config()
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "file"
            path.write_text(
                "<yml_catalog><shop><offers>"
                + "".join(
                    f'<offer id="{i}"><vendorCode>A</vendorCode><name>Item</name><price>1</price></offer>'
                    for i in range(3)
                )
                + "</offers></shop></yml_catalog>"
            )
            with self.assertRaises(MappingValidationError):
                list(
                    SourceParser(ImportOptions(max_rows=2)).rows(
                        path, "xml", source, mapping
                    )
                )
            with self.assertRaises(MappingValidationError):
                list(
                    SourceParser(ImportOptions(max_record_bytes=32)).rows(
                        path, "xml", source, mapping
                    )
                )
            async with aclosing(
                SourceParser(ImportOptions(batch_max_bytes=200)).batches(
                    path, "xml", source, mapping
                )
            ) as stream:
                async for batch in stream:
                    self.assertEqual(len(batch), 1)

    async def test_xlsx_shared_strings_and_cached_formula(self):
        from zipfile import ZipFile

        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "file"
            with ZipFile(path, "w") as z:
                z.writestr(
                    "xl/workbook.xml",
                    '<workbook xmlns:r="urn:rel"><sheets><sheet name="Sheet1" r:id="one"/></sheets></workbook>',
                )
                z.writestr(
                    "xl/_rels/workbook.xml.rels",
                    '<Relationships><Relationship Id="one" Target="worksheets/sheet1.xml"/></Relationships>',
                )
                z.writestr(
                    "xl/sharedStrings.xml",
                    "<sst>"
                    + "".join(
                        f"<si><t>{s}</t></si>"
                        for s in (
                            "external_id",
                            "sku",
                            "title",
                            "purchase_price",
                            "ID",
                            "SKU",
                            "Title",
                        )
                    )
                    + "</sst>",
                )
                z.writestr(
                    "xl/worksheets/sheet1.xml",
                    '<worksheet><sheetData><row r="1"><c r="A1" t="s"><v>0</v></c><c r="B1" t="s"><v>1</v></c><c r="C1" t="s"><v>2</v></c><c r="D1" t="s"><v>3</v></c></row><row r="2"><c r="A2" t="s"><v>4</v></c><c r="B2" t="s"><v>5</v></c><c r="C2" t="s"><v>6</v></c><c r="D2"><f>5+5</f><v>10</v></c></row></sheetData></worksheet>',
                )
            rows = list(
                SourceParser().rows(
                    path, "xlsx", {"sheet_name": "Sheet1"}, self.mapping()
                )
            )
            self.assertEqual(rows[0].normalized["purchase_price"], Decimal("10.0000"))
            self.assertFalse(rows[0].errors)
            self.assertEqual(list(Path(d).iterdir()), [path])


@unittest.skipUnless(
    os.environ.get("PRICE_LIST_SAMPLE_XML")
    and os.environ.get("PRICE_LIST_SAMPLE_XLSX"),
    "Set PRICE_LIST_SAMPLE_XML and PRICE_LIST_SAMPLE_XLSX to downloaded partner samples.",
)
class PartnerPriceListRealSampleTests(unittest.TestCase):
    def test_real_partner_samples(self) -> None:
        parser = SourceParser()
        source, mapping = prom_xml_config()
        xml_rows = list(
            parser.rows(
                Path(os.environ["PRICE_LIST_SAMPLE_XML"]),
                "xml",
                source,
                mapping,
                limit=3,
            )
        )
        self.assertEqual(len(xml_rows), 3)
        self.assertFalse(xml_rows[0].errors)
        xlsx_mapping = {
            "external_id": {"selector": "Артикул", "required": True},
            "sku": {"selector": "Артикул", "required": True},
            "title": {
                "selectors": ["Название (UA)", "Название (RU)"],
                "required": True,
            },
            "purchase_price": {"selector": "Цена", "required": True},
            "rrp": {"selector": "РРЦ"},
            "currency": {"selector": "Валюта", "default": "UAH", "required": True},
            "availability": {"selector": "Наличие"},
            "quantity": {"selector": "Количество"},
        }
        xlsx_rows = list(
            parser.rows(
                Path(os.environ["PRICE_LIST_SAMPLE_XLSX"]),
                "xlsx",
                {"sheet_name": "Sheet1", "header_row": 1, "data_start_row": 2},
                xlsx_mapping,
                limit=3,
            )
        )
        self.assertEqual(len(xlsx_rows), 3)
        self.assertFalse(xlsx_rows[0].errors)


__all__ = [
    "PartnerPriceListDomainTests",
    "PartnerPriceListParserTests",
    "PartnerPriceListFetcherTests",
    "PartnerPriceListRealSampleTests",
]


class SourceSafetyRegressionTests(unittest.IsolatedAsyncioTestCase):
    async def test_download_pins_dns_and_preserves_tls_name_and_cleans_file(self):
        import httpx
        import asyncio
        import socket
        from unittest.mock import AsyncMock, patch
        from src.modules.price_lists.infrastructure.source.fetcher import (
            HttpRemoteFileFetcher,
        )

        original_client = httpx.AsyncClient
        calls = []

        def serve(request):
            calls.append(request)
            return httpx.Response(200, content=b"<offers/>")

        def client(**kwargs):
            return original_client(transport=httpx.MockTransport(serve), **kwargs)

        resolver = AsyncMock(
            return_value=[
                (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443))
            ]
        )
        with (
            patch.object(asyncio.get_running_loop(), "getaddrinfo", resolver),
            patch("httpx.AsyncClient", client),
        ):
            async with HttpRemoteFileFetcher().open(
                "https://example.com/prices?token=secret"
            ) as source:
                path = source.path
                self.assertEqual(path.read_bytes(), b"<offers/>")
            self.assertFalse(path.exists())
        self.assertEqual(resolver.await_count, 1)
        self.assertEqual(calls[0].url.host, "93.184.216.34")
        self.assertEqual(calls[0].headers["host"], "example.com")
        self.assertEqual(calls[0].extensions["sni_hostname"], "example.com")

    async def test_preview_cancellation_stops_disk_parser(self):
        import asyncio
        import threading
        from unittest.mock import patch
        from src.modules.price_lists.infrastructure.source.parser import SourceParser

        parser = SourceParser()
        started = threading.Event()
        stopped = threading.Event()

        def inspect(path, source_format, source_config, stop=None):
            started.set()
            stop.wait(2)
            stopped.set()
            return {}

        with patch.object(parser, "inspect", inspect):
            task = asyncio.create_task(parser.inspect_source(None, "xlsx", {}))
            await asyncio.to_thread(started.wait, 1)
            task.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await task
        self.assertTrue(stopped.is_set())

    def test_mapping_zero_based_column_and_invalid_selector(self):
        from src.modules.price_lists.domain.offer.mapping import normalize_row
        from src.modules.price_lists.domain.price_list.value_object.configuration import (
            MappingConfigurationVO,
        )
        from src.modules.price_lists.domain.price_list.error import (
            PriceListValidationError,
        )

        mapping = {
            name: {"constant": value}
            for name, value in dict(
                external_id="1", sku="S", title="T", purchase_price="10", currency="UAH"
            ).items()
        }
        mapping["external_id"] = {"selector": 0}
        MappingConfigurationVO(mapping)
        normalized, errors = normalize_row({"first": "identifier"}, mapping)
        self.assertFalse(errors)
        self.assertEqual(normalized["external_id"], "identifier")
        mapping["external_id"] = {"selector": -1}
        with self.assertRaises(PriceListValidationError):
            MappingConfigurationVO(mapping)

    def test_yaml_merge_and_container_expansion_are_bounded(self):
        from io import BytesIO
        from src.modules.price_lists.infrastructure.source.yaml_stream import (
            YamlRecords,
        )
        from src.modules.price_lists.domain.price_list.error import (
            MappingValidationError,
        )

        rows = list(
            YamlRecords(
                BytesIO(
                    b"base: &base {price: 10, name: inherited}\noffers:\n  - {<<: *base, name: explicit}\n"
                ),
                "offers",
                10000,
            ).rows()
        )
        self.assertEqual(rows[0][1], {"price": 10, "name": "explicit"})
        source = b"offers:\n  - [" + b"{}," * 1000 + b"{}]\n"
        with self.assertRaises(MappingValidationError):
            list(YamlRecords(BytesIO(source), "offers", 1000).rows())
