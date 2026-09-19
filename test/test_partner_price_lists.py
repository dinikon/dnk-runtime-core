from __future__ import annotations

import os
import tempfile
import unittest
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from uuid import UUID, uuid4
from unittest.mock import AsyncMock, Mock, patch

from openpyxl import Workbook
from cryptography.fernet import Fernet
from sqlalchemy.dialects import postgresql

from src.modules.price_lists.application import (
    PriceListService,
    PriceListStateConflict,
    cron_occurrences,
    next_cron_occurrence,
)
from src.modules.price_lists.domain import (
    MappingValidationError,
    canonical_state_hash,
    deterministic_cleanup_job_id,
    deterministic_job_id,
    mask_source_url,
    normalize_availability,
)
from src.modules.price_lists.infrastructure.source import (
    HttpRemoteFileFetcher,
    SourceParser,
    SourceUrlCipher,
    prom_xml_config,
)
from src.modules.price_lists.infrastructure.persistence.models import (
    PriceListSyncItemModel,
)
from src.modules.price_lists.infrastructure.persistence.repository import (
    PRICE_LIST_WRITE_BATCH_SIZE,
    SqlAlchemyPriceListRepository,
)
from src.modules.price_lists.presentation.jobs.handler import PriceListSyncJobHandler
from src.modules.shared.domain.jobs import ScheduledJob


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
        next_at = next_cron_occurrence(
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
        with self.assertRaisesRegex(ValueError, "at least 15 minutes"):
            cron_occurrences("*/5 * * * *", "Europe/Kyiv")


class PartnerPriceListParserTests(unittest.TestCase):
    def setUp(self) -> None:
        self.parser = SourceParser()

    def test_prom_xml_preset_parses_attributes_and_prices(self) -> None:
        source, mapping = prom_xml_config()
        xml = b"""<?xml version='1.0'?>
        <!DOCTYPE yml_catalog SYSTEM 'shops.dtd'>
        <yml_catalog><shop><offers>
          <offer id='42' in_stock='true'><vendorCode>SKU-42</vendorCode>
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

    def test_xml_parser_matches_the_full_configured_item_path(self) -> None:
        source, mapping = prom_xml_config()
        xml = b"""<yml_catalog><metadata><offer id='wrong'/></metadata><shop>
        <offers><offer id='right' in_stock='false'><vendorCode>SKU</vendorCode>
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
        with self.assertRaisesRegex(ValueError, "Credentials"):
            await fetcher._validate_url("https://user:password@example.com/file.xml")
        with self.assertRaisesRegex(ValueError, "non-public"):
            await fetcher._validate_url("https://127.0.0.1/file.xml")


class PartnerPriceListSettingsTests(unittest.IsolatedAsyncioTestCase):
    def _price_list(self, *, status: str = "paused") -> dict:
        return {
            "id": uuid4(),
            "status": status,
            "source_url_secret": "encrypted-source",
            "source_format": "xlsx",
            "source_preset": None,
            "source_config": {
                "sheet_name": "Sheet1",
                "header_row": 1,
                "data_start_row": 2,
            },
            "mapping_config": {
                "external_id": {"selector": "SKU"},
                "sku": {"selector": "SKU"},
                "title": {"selector": "Title"},
                "purchase_price": {"selector": "Price"},
                "currency": {"selector": "Currency"},
            },
            "mapping_version": 3,
            "schedule_revision": 7,
        }

    async def test_paused_settings_update_keeps_secret_and_does_not_fetch_unchanged_source(
        self,
    ) -> None:
        current = self._price_list()
        repository = AsyncMock()
        repository.get.return_value = current
        fetcher = AsyncMock()
        service = PriceListService(repository, fetcher=fetcher)
        cipher = Mock()
        cipher.decrypt.return_value = "https://partner.example/current.xlsx"

        with patch(
            "src.modules.price_lists.application.service.SourceUrlCipher",
            return_value=cipher,
        ):
            await service.update_settings(
                tenant_id=uuid4(),
                actor_id=uuid4(),
                price_list_id=current["id"],
                title=" Updated title ",
                source_url=None,
                source_format="xlsx",
                source_preset=None,
                source_config=current["source_config"],
                mapping_config=current["mapping_config"],
                cron_expression="0 */6 * * *",
                timezone="Europe/Kyiv",
                new_item_policy="create",
                missing_item_policy="mark_out_of_stock",
                missing_threshold=2,
            )

        fetcher.fetch.assert_not_awaited()
        values = repository.update_config.await_args.kwargs["values"]
        self.assertEqual(values["title"], "Updated title")
        self.assertEqual(values["status"], "paused")
        self.assertEqual(values["schedule_revision"], 8)
        self.assertIsNone(values["next_sync_at"])
        self.assertNotIn("source_url_secret", values)
        self.assertNotIn("mapping_version", values)

    async def test_active_and_archived_settings_updates_are_rejected(self) -> None:
        for status in ("active", "archived"):
            repository = AsyncMock()
            current = self._price_list(status=status)
            repository.get.return_value = current
            service = PriceListService(repository)

            with self.assertRaises(PriceListStateConflict):
                await service.update_settings(
                    tenant_id=uuid4(),
                    actor_id=uuid4(),
                    price_list_id=current["id"],
                    title="Title",
                    source_url=None,
                    source_format="xlsx",
                    source_preset=None,
                    source_config=current["source_config"],
                    mapping_config=current["mapping_config"],
                    cron_expression="0 */6 * * *",
                    timezone="Europe/Kyiv",
                    new_item_policy="create",
                    missing_item_policy="mark_out_of_stock",
                    missing_threshold=2,
                )
            repository.update_config.assert_not_awaited()

    async def test_paused_schedule_stays_paused_without_next_run(self) -> None:
        current = self._price_list()
        repository = AsyncMock()
        repository.get.return_value = current

        await PriceListService(repository).save_schedule(
            tenant_id=uuid4(),
            actor_id=uuid4(),
            price_list_id=current["id"],
            cron_expression="0 */6 * * *",
            timezone="Europe/Kyiv",
            new_item_policy="create",
            missing_item_policy="mark_out_of_stock",
            missing_threshold=2,
        )

        values = repository.update_config.await_args.kwargs["values"]
        self.assertIsNone(values["next_sync_at"])
        self.assertEqual(values["schedule_revision"], 8)

    async def test_active_schedule_conflict_is_checked_before_cron(self) -> None:
        current = self._price_list(status="active")
        repository = AsyncMock()
        repository.get.return_value = current

        with self.assertRaises(PriceListStateConflict):
            await PriceListService(repository).save_schedule(
                tenant_id=uuid4(),
                actor_id=uuid4(),
                price_list_id=current["id"],
                cron_expression="not a cron",
                timezone="Europe/Kyiv",
                new_item_policy="create",
                missing_item_policy="mark_out_of_stock",
                missing_threshold=2,
            )

        repository.update_config.assert_not_awaited()


class PartnerPriceListLargeImportTests(unittest.IsolatedAsyncioTestCase):
    async def test_staging_insert_is_split_below_asyncpg_parameter_limit(self) -> None:
        session = AsyncMock()
        repository = SqlAlchemyPriceListRepository(session)
        tenant_id = uuid4()
        run_id = uuid4()
        values = [
            {
                "sync_run_id": run_id,
                "row_number": row_number,
                "external_id": str(row_number),
                "sku": f"SKU-{row_number}",
                "title": f"Offer {row_number}",
                "purchase_price": Decimal("1"),
                "rrp": Decimal("2"),
                "currency": "UAH",
                "availability": "in_stock",
                "quantity": None,
                "value_hash": "a" * 64,
                "normalized_payload": {},
                "validation_errors": [],
            }
            for row_number in range(1, 8_400)
        ]

        await repository._insert_many(
            tenant_id=tenant_id,
            table=PriceListSyncItemModel.__table__,
            values=values,
        )

        self.assertEqual(session.execute.await_count, 9)
        for call in session.execute.await_args_list:
            statement = call.args[0]
            compiled = statement.compile(dialect=postgresql.dialect())
            self.assertLessEqual(len(compiled.params), 32_767)
            self.assertLessEqual(
                len(statement._multi_values[0]), PRICE_LIST_WRITE_BATCH_SIZE
            )

    async def test_sync_failure_is_not_masked_by_duration_metric(self) -> None:
        class Session:
            commit = AsyncMock()

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, traceback):
                return None

        class Repository:
            get_run_by_job = AsyncMock(return_value=None)
            create_run = AsyncMock(return_value=uuid4())
            finish_run = AsyncMock()

        class FailingFetcher:
            async def fetch(self, url: str):
                raise ValueError("source download failed")

        repository = Repository()
        handler = PriceListSyncJobHandler(lambda: Session(), fetcher=FailingFetcher())
        now = datetime.now(UTC)
        job = ScheduledJob(
            id=uuid4(),
            tenant_id=uuid4(),
            job_type="price_list.sync",
            payload={},
            run_at=now,
            status="running",
            attempts=1,
            locked_until=now,
            lock_token="lease",
            created_at=now,
            updated_at=now,
        )
        cipher = SourceUrlCipher(Fernet.generate_key().decode("ascii"))

        with (
            patch(
                "src.modules.price_lists.presentation.jobs.handler."
                "SqlAlchemyPriceListRepository",
                return_value=repository,
            ),
            patch(
                "src.modules.price_lists.presentation.jobs.handler.SourceUrlCipher",
                return_value=cipher,
            ),
        ):
            with self.assertRaisesRegex(ValueError, "source download failed"):
                await handler._synchronize(
                    job,
                    uuid4(),
                    1,
                    "manual",
                    {
                        "source_url_secret": cipher.encrypt(
                            "https://partner.example/feed.xml"
                        ),
                        "source_format": "xml",
                    },
                )

        repository.finish_run.assert_awaited_once()


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
