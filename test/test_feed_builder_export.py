"""Проверяет общий результат предпросмотра и пробного CSV."""

import csv
from dataclasses import replace
from datetime import datetime
from decimal import Decimal
from io import StringIO
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, patch
from uuid import UUID, uuid4

from src.modules.feed_builder.application.feed.export_settings import settings_to_dto
from src.modules.feed_builder.application.feed.query.download_test_csv.handler import (
    DownloadTestCsvHandler,
)
from src.modules.feed_builder.application.feed.query.download_test_csv.query import (
    DownloadTestCsvQuery,
)
from src.modules.feed_builder.application.feed.query.get_feed.dto import FeedDetailsDTO
from src.modules.feed_builder.application.feed.query.preview_feed.handler import (
    PreviewFeedHandler,
)
from src.modules.feed_builder.application.feed.query.preview_feed.query import (
    PreviewFeedQuery,
)
from src.modules.feed_builder.application.feed.graph.codec import schema_document
from src.modules.feed_builder.application.feed.graph.codec import decode_schema
from src.modules.feed_builder.application.feed.service.publication_export import (
    PublicationExportService,
)
from src.modules.feed_builder.application.publication.port.export_source import (
    CatalogReference,
    PublicationCursor,
    PublicationExportSource,
)
from src.modules.feed_builder.domain.feed.enum.catalog_source_path import (
    CatalogSourcePath,
)
from src.modules.feed_builder.domain.feed.enum.locale_fallback_mode import (
    LocaleFallbackMode,
)
from src.modules.feed_builder.domain.feed.enum.source_provider import SourceProvider
from src.modules.feed_builder.domain.feed.enum.transform_operation import (
    TransformOperation,
)
from src.modules.feed_builder.domain.feed.value_object.export_name import ExportNameVO
from src.modules.feed_builder.domain.feed.value_object.feed_id import FeedIdVO
from src.modules.feed_builder.domain.feed.value_object.feed_schema import FeedSchemaVO
from src.modules.feed_builder.domain.feed.value_object.field_export_settings import (
    FieldExportSettingsVO,
)
from src.modules.feed_builder.domain.feed.value_object.field_key import FieldKeyVO
from src.modules.feed_builder.domain.feed.value_object.locale_code import LocaleCodeVO
from src.modules.feed_builder.domain.feed.field_node.money.value_object.data import (
    MoneyNodeDataVO,
)
from src.modules.feed_builder.domain.feed.value_object.locale_fallback_policy import (
    LocaleFallbackPolicyVO,
)
from src.modules.feed_builder.domain.feed.expression.value_object.parameter_reference import (
    ParameterReferenceVO,
)
from src.modules.feed_builder.domain.feed.expression.value_object.price_calculation import (
    PriceCalculationVO,
)
from src.modules.feed_builder.domain.feed.value_object.source_reference import (
    SourceReferenceVO,
)
from src.modules.feed_builder.domain.feed.value_object.source_value_definition import (
    SourceValueDefinitionVO,
)
from src.modules.feed_builder.domain.feed.field_node.short_text.value_object.data import (
    ShortTextNodeDataVO,
)
from src.modules.feed_builder.domain.feed.value_object.text_constraints import (
    TextConstraintsVO,
)
from src.modules.feed_builder.domain.feed.field_node.long_text.value_object.data import (
    LongTextNodeDataVO,
)
from src.modules.feed_builder.domain.feed.value_object.transform_definition import (
    TransformDefinitionVO,
)
from src.modules.feed_builder.domain.publication.value_object.publication_catalog_snapshot import (
    PublicationCatalogSnapshotVO,
)
from src.modules.feed_builder.infrastructure.feed.serialization.test_csv import (
    TemporaryCsvStorage,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from test.test_feed_builder_calculation import (
    A,
    C,
    V,
    binary,
    calculation_field,
    inputs,
    number,
)
from test.test_feed_builder_domain import (
    NOW,
    ComparisonConditionVO,
    ScalarLiteralVO,
    feed,
    money_field,
    rule,
    text_field,
)


class FeedExportTests(IsolatedAsyncioTestCase):
    """Проверяет лимит образца, общее разрешение значений и строгий CSV."""

    def setUp(self) -> None:
        """Готовит фид с локалями, категорией, независимыми ценами и ручным полем."""
        category = EntityIdVO(uuid4())
        title = text_field(
            "name",
            type_definition=ShortTextNodeDataVO(
                SourceValueDefinitionVO(
                    SourceReferenceVO(SourceProvider.CATALOG, CatalogSourcePath.TITLE)
                ),
                constraints=TextConstraintsVO(required=True),
                locale=LocaleCodeVO("uk"),
                fallback_policy=LocaleFallbackPolicyVO(
                    LocaleFallbackMode.LOCALE_CHAIN, (LocaleCodeVO("ru"),)
                ),
                transforms=(TransformDefinitionVO(TransformOperation.STRING_TRIM),),
            ),
        )
        description = text_field(
            "details",
            type_definition=LongTextNodeDataVO(
                SourceValueDefinitionVO(
                    SourceReferenceVO(
                        SourceProvider.CATALOG, CatalogSourcePath.DESCRIPTION
                    )
                ),
                locale=LocaleCodeVO("uk"),
            ),
        )
        regular = replace(
            calculation_field(),
            key=FieldKeyVO("retail"),
            export=FieldExportSettingsVO(ExportNameVO("retail")),
        )
        partner = money_field(
            PriceCalculationVO(
                ParameterReferenceVO("price.regular"),
                (
                    rule(
                        ComparisonConditionVO(
                            C.CONTAINS,
                            ParameterReferenceVO("product.category_ids"),
                            ScalarLiteralVO(V.UUID, category),
                        ),
                        binary(
                            A.MULTIPLY,
                            ParameterReferenceVO("price.purchase"),
                            number("1.25"),
                        ),
                    ),
                ),
            )
        )
        aggregate = feed(
            FeedSchemaVO((title, description, regular, partner, text_field("note")))
        )
        self.details = FeedDetailsDTO(
            aggregate.id.uuid,
            aggregate.name.value,
            aggregate.code.value,
            aggregate.status.value,
            settings_to_dto(aggregate.export_settings),
            schema_document(aggregate.schema),
            aggregate.version.value,
            NOW,
            NOW,
        )
        self.items = tuple(
            PublicationExportSource(uuid4(), (uuid4(), None), (), NOW)
            for _ in range(23)
        )
        self.snapshots = {
            item.reference: PublicationCatalogSnapshotVO(
                replace(
                    inputs("800"),
                    sku=f"sku-{index + 1}",
                    purchase=Decimal("0"),
                    category_ids=(category,),
                ),
                (
                    ("item.title", "ru", "  Тест  "),
                    ("item.description", "uk", 'Рядок, "два"\nтри'),
                ),
            )
            for index, item in enumerate(self.items)
        }
        self.feed_repo = AsyncMock()
        self.feed_repo.get_details.return_value = self.details
        self.publications = AsyncMock()
        self.publications.count_enabled.return_value = len(self.items)
        self.publications.read_enabled.side_effect = self.read_items
        self.catalog = AsyncMock()
        self.catalog.read.side_effect = self.read_catalog
        self.access = AsyncMock()
        clock = type("Clock", (), {"now": lambda self: NOW})()
        service = PublicationExportService(
            self.feed_repo, self.publications, self.catalog, self.access, clock
        )
        self.preview = PreviewFeedHandler(service)
        self.download = DownloadTestCsvHandler(service, TemporaryCsvStorage())

    async def read_items(
        self,
        feed_id: FeedIdVO,
        limit: int,
        before: PublicationCursor | None,
    ) -> tuple[PublicationExportSource, ...]:
        """Возвращает увязанный с курсором тестовый пакет."""
        self.assertEqual(feed_id.uuid, self.details.id)
        start = 0
        if before is not None:
            start = next(
                index + 1
                for index, item in enumerate(self.items)
                if item.id == before[1]
            )
        return self.items[start : start + limit]

    async def read_catalog(
        self,
        references: tuple[CatalogReference, ...],
        as_of: datetime,
        locales: frozenset[str],
        sources: frozenset[str],
    ) -> dict[CatalogReference, PublicationCatalogSnapshotVO]:
        """Проверяет одно пакетное чтение с общим временем и нужными локалями."""
        self.assertEqual(as_of, NOW)
        self.assertEqual(locales, {"ru", "uk"})
        self.assertEqual(sources, {"item.title", "item.description"})
        return {ref: self.snapshots[ref] for ref in references if ref in self.snapshots}

    async def test_preview_limits_read_and_matches_complete_file(self) -> None:
        """Первые 20 строк совпадают, при скачивании включается весь ассортимент."""
        preview = await self.preview.execute(
            PreviewFeedQuery(FeedIdVO(self.details.id), self.details.version)
        )
        self.assertEqual(preview.total_enabled, 23)
        self.assertEqual(len(preview.rows), 20)
        self.catalog.read.assert_awaited_once()
        self.assertEqual(len(self.catalog.read.await_args.args[0]), 20)
        first = preview.rows[0]
        self.assertEqual(
            first.values, ("Тест", 'Рядок, "два"\nтри', "880.00 UAH", "0.00 UAH", None)
        )
        result = await self.download.execute(
            DownloadTestCsvQuery(FeedIdVO(self.details.id), self.details.version)
        )
        self.assertIsNotNone(result.file)
        contents = b"".join(result.file.chunks()).decode("utf-8")
        rows = list(csv.reader(StringIO(contents)))
        self.assertEqual(rows[0], [column.name for column in preview.columns])
        self.assertEqual(len(rows), 24)
        self.assertEqual(
            rows[1:21],
            [
                [value if value is not None else "" for value in row.values]
                for row in preview.rows
            ],
        )

    async def test_issue_after_sample_blocks_file(self) -> None:
        """Показывает адрес ошибки в 21-й строке и закрывает временный файл."""
        missing = self.items[20]
        self.snapshots[missing.reference] = replace(
            self.snapshots[missing.reference], texts=()
        )
        preview = await self.preview.execute(
            PreviewFeedQuery(FeedIdVO(self.details.id), self.details.version)
        )
        self.assertTrue(all(not row.issues for row in preview.rows))
        result = await self.download.execute(
            DownloadTestCsvQuery(FeedIdVO(self.details.id), self.details.version)
        )
        self.assertIsNone(result.file)
        self.assertEqual(result.issues[0].publication_id, missing.id)
        self.assertEqual(result.issues[0].field_name, "name")
        self.assertEqual(result.issues[0].code, "REQUIRED_VALUE_MISSING")

    async def test_csv_preview_preserves_formula_like_text_and_explains_block(
        self,
    ) -> None:
        """Опасный текст остаётся виден, а пробный CSV отклоняется с причиной."""
        first = self.items[0]
        self.snapshots[first.reference] = replace(
            self.snapshots[first.reference],
            texts=(("item.title", "ru", "=1+1"),),
        )
        query = PreviewFeedQuery(FeedIdVO(self.details.id), self.details.version)
        preview = await self.preview.execute(query)
        self.assertEqual(preview.rows[0].values[0], "=1+1")
        self.assertEqual(preview.rows[0].issues[0].code, "CSV_FORMULA_LIKE_TEXT")
        result = await self.download.execute(
            DownloadTestCsvQuery(query.feed_id, query.expected_version)
        )
        self.assertIsNone(result.file)
        self.assertEqual(result.issues[0].publication_id, first.id)
        self.assertEqual(result.issues[0].field_name, "name")

    async def test_text_only_feed_exports_batches_with_large_unused_prices(
        self,
    ) -> None:
        """Фид без цен экспортирует все страницы, даже если цены Catalog вне бюджета."""
        schema = decode_schema(self.details.schema)
        self.details = replace(
            self.details,
            schema=schema_document(
                FeedSchemaVO(
                    tuple(
                        field
                        for field in schema.fields
                        if not isinstance(field.type_definition, MoneyNodeDataVO)
                    )
                )
            ),
        )
        self.feed_repo.get_details.return_value = self.details
        first = self.items[0]
        snapshot = self.snapshots[first.reference]
        self.snapshots[first.reference] = replace(
            snapshot,
            inputs=replace(snapshot.inputs, regular=Decimal("1" * 41)),
        )
        query = DownloadTestCsvQuery(FeedIdVO(self.details.id), self.details.version)
        with patch(
            "src.modules.feed_builder.application.feed.query.download_test_csv.handler._BATCH_SIZE",
            10,
        ):
            result = await self.download.execute(query)
        self.assertIsNotNone(result.file)
        rows = list(csv.reader(StringIO(b"".join(result.file.chunks()).decode())))
        self.assertEqual(rows[0], ["name", "details", "note"])
        self.assertEqual(len(rows), 24)
        self.assertEqual(self.catalog.read.await_count, 3)
