"""Поведение, сценарии и JSON round-trip первой вертикали Feed CRUD."""

import copy
import json
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4
import unittest

from test.test_feed_builder_domain import feed, text_field, money_field, rule, NOW, UAH
from src.modules.feed_builder.application.feed.port.settings_repository import (
    LockedFeedSettings,
)
from src.modules.feed_builder.domain.feed.aggregate import Feed
from src.modules.feed_builder.domain.feed.enum.feed_status import FeedStatus
from src.modules.feed_builder.domain.feed.value_object.feed_version import FeedVersionVO
from src.modules.feed_builder.domain.feed.value_object.feed_id import FeedIdVO
from src.modules.feed_builder.domain.feed.value_object.feed_name import FeedNameVO
from src.modules.feed_builder.domain.feed.value_object.feed_code import FeedCodeVO
from src.modules.feed_builder.domain.feed.value_object.feed_schema import FeedSchemaVO
from src.modules.feed_builder.domain.feed.value_object.feed_export_settings import (
    FeedExportSettingsVO,
)
from src.modules.feed_builder.domain.feed.value_object.csv_export_settings import (
    CsvExportSettingsVO,
)
from src.modules.feed_builder.domain.feed.value_object.xml_export_settings import (
    XmlExportSettingsVO,
)
from src.modules.feed_builder.domain.feed.value_object.export_name import ExportNameVO
from src.modules.feed_builder.domain.feed.expression.value_object.price_calculation import (
    PriceCalculationVO,
)
from src.modules.feed_builder.domain.feed.expression.value_object.parameter_reference import (
    ParameterReferenceVO,
)
from src.modules.feed_builder.domain.feed.expression.value_object.decimal_literal import (
    DecimalLiteralVO,
)
from src.modules.feed_builder.domain.feed.expression.value_object.scalar_literal import (
    ScalarLiteralVO,
)
from src.modules.feed_builder.domain.feed.expression.value_object.collection_literal import (
    CollectionLiteralVO,
)
from src.modules.feed_builder.domain.feed.expression.value_object.arithmetic_expression import (
    ArithmeticExpressionVO,
)
from src.modules.feed_builder.domain.feed.expression.value_object.function_expression import (
    FunctionExpressionVO,
)
from src.modules.feed_builder.domain.feed.expression.value_object.comparison_condition import (
    ComparisonConditionVO,
)
from src.modules.feed_builder.domain.feed.expression.value_object.logical_condition import (
    LogicalConditionVO,
)
from src.modules.feed_builder.domain.feed.expression.value_object.presence_condition import (
    PresenceConditionVO,
)
from src.modules.feed_builder.domain.feed.expression.value_object.purchase_price_source import (
    PurchasePriceSourceVO,
)
from src.modules.feed_builder.domain.feed.field_node.short_text.value_object.data import (
    ShortTextNodeDataVO,
)
from src.modules.feed_builder.domain.feed.field_node.long_text.value_object.data import (
    LongTextNodeDataVO,
)
from src.modules.feed_builder.domain.feed.value_object.manual_value_definition import (
    ManualValueDefinitionVO,
)
from src.modules.feed_builder.domain.feed.value_object.source_value_definition import (
    SourceValueDefinitionVO,
)
from src.modules.feed_builder.domain.feed.value_object.source_reference import (
    SourceReferenceVO,
)
from src.modules.feed_builder.domain.feed.value_object.money_value_definition import (
    MoneyValueDefinitionVO,
)
from src.modules.feed_builder.domain.feed.enum.money_value_mode import MoneyValueMode
from src.modules.feed_builder.domain.feed.enum.source_provider import SourceProvider
from src.modules.feed_builder.domain.feed.enum.catalog_source_path import (
    CatalogSourcePath,
)
from src.modules.feed_builder.domain.feed.value_object.locale_code import LocaleCodeVO
from src.modules.feed_builder.domain.feed.value_object.locale_fallback_policy import (
    LocaleFallbackPolicyVO,
)
from src.modules.feed_builder.domain.feed.value_object.transform_definition import (
    TransformDefinitionVO,
)
from src.modules.feed_builder.domain.feed.value_object.truncate_parameters import (
    TruncateParametersVO,
)
from src.modules.feed_builder.domain.feed.value_object.money_ceil_step_parameters import (
    MoneyCeilStepParametersVO,
)
from src.modules.feed_builder.domain.feed.expression.enum.literal_value_type import (
    LiteralValueType,
)
from src.modules.feed_builder.domain.feed.expression.enum.logical_operator import (
    LogicalOperator,
)
from src.modules.feed_builder.domain.feed.expression.enum.comparison_operator import (
    ComparisonOperator,
)
from src.modules.feed_builder.domain.feed.expression.enum.arithmetic_operator import (
    ArithmeticOperator,
)
from src.modules.feed_builder.domain.feed.expression.enum.presence_operator import (
    PresenceOperator,
)
from src.modules.feed_builder.domain.feed.expression.enum.price_function import (
    PriceFunction,
)
from src.modules.feed_builder.domain.feed.enum.locale_fallback_mode import (
    LocaleFallbackMode,
)
from src.modules.feed_builder.domain.feed.enum.transform_operation import (
    TransformOperation,
)
from src.modules.feed_builder.domain.feed.error import (
    FeedArchivedError,
    FeedVersionConflictError,
    FeedNotFoundError,
    InvalidFeedValueError,
)
from src.modules.feed_builder.application.feed.command.create_feed.command import (
    CreateFeedCommand,
)
from src.modules.feed_builder.application.feed.command.create_feed.handler import (
    CreateFeedHandler,
)
from src.modules.feed_builder.application.feed.command.update_feed.command import (
    UpdateFeedCommand,
)
from src.modules.feed_builder.application.feed.command.update_feed.handler import (
    UpdateFeedHandler,
)
from src.modules.feed_builder.application.feed.command.archive_feed.command import (
    ArchiveFeedCommand,
)
from src.modules.feed_builder.application.feed.command.archive_feed.handler import (
    ArchiveFeedHandler,
)
from src.modules.feed_builder.application.feed.query.get_feed.query import GetFeedQuery
from src.modules.feed_builder.application.feed.query.get_feed.handler import (
    GetFeedHandler,
)
from src.modules.feed_builder.application.feed.query.list_feeds.query import (
    ListFeedsQuery,
)
from src.modules.feed_builder.application.feed.query.list_feeds.handler import (
    ListFeedsHandler,
)
from src.modules.feed_builder.application.feed.export_settings_dto import (
    FeedExportSettingsDTO,
    CsvExportSettingsDTO,
    XmlExportSettingsDTO,
)
from src.modules.feed_builder.application.feed.graph.codec import schema_document
from src.modules.feed_builder.infrastructure.feed.persistence.mapper import FeedMapper
from src.modules.feed_builder.domain.feed.enum.feed_access_mode import FeedAccessMode
from src.modules.feed_builder.infrastructure.feed.persistence.query_mapper import (
    FeedQueryMapper,
)
from src.modules.feed_builder.infrastructure.feed.persistence.graph_mapper import (
    decode_schema,
)
from src.modules.feed_builder.infrastructure.feed.persistence.error import (
    InvalidFeedStorageError,
)
from src.modules.feed_builder.presentation.feed.http.request.create_feed import (
    CreateFeedRequest,
)
from src.modules.feed_builder.presentation.feed.http.request.patch_feed import (
    PatchFeedRequest,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from pydantic import ValidationError


def rich_feed() -> Feed:
    """Собирает четыре поля с локалями, всеми видами параметров и закупочной формулой."""
    category = EntityIdVO(uuid4())
    condition = LogicalConditionVO(
        LogicalOperator.ALL,
        (
            ComparisonConditionVO(
                ComparisonOperator.IN,
                ScalarLiteralVO(LiteralValueType.UUID, category),
                CollectionLiteralVO(
                    LiteralValueType.UUID,
                    (ScalarLiteralVO(LiteralValueType.UUID, category),),
                ),
            ),
            LogicalConditionVO(
                LogicalOperator.ANY,
                (
                    PresenceConditionVO(
                        PresenceOperator.EXISTS, ParameterReferenceVO("price.purchase")
                    ),
                    LogicalConditionVO(
                        LogicalOperator.NOT,
                        (
                            ComparisonConditionVO(
                                ComparisonOperator.EQ,
                                ScalarLiteralVO(LiteralValueType.BOOLEAN, True),
                                ScalarLiteralVO(LiteralValueType.BOOLEAN, False),
                            ),
                        ),
                    ),
                ),
            ),
        ),
    )
    expression = FunctionExpressionVO(
        PriceFunction.MAX,
        (
            ArithmeticExpressionVO(
                ArithmeticOperator.ADD,
                left=ArithmeticExpressionVO(
                    ArithmeticOperator.DIVIDE,
                    left=ParameterReferenceVO("price.regular"),
                    right=DecimalLiteralVO(Decimal("40.123456")),
                ),
                right=DecimalLiteralVO(Decimal("50.123456")),
            ),
            FunctionExpressionVO(
                PriceFunction.ABS,
                (
                    ArithmeticExpressionVO(
                        ArithmeticOperator.NEGATE,
                        operand=ParameterReferenceVO("price.purchase"),
                    ),
                ),
            ),
        ),
    )
    calculation = PriceCalculationVO(
        default_expression=ArithmeticExpressionVO(
            ArithmeticOperator.SUBTRACT,
            left=ParameterReferenceVO("price.regular"),
            right=DecimalLiteralVO(Decimal("1.123456")),
        ),
        rules=(rule(condition, expression),),
        purchase_source=PurchasePriceSourceVO(EntityIdVO(uuid4())),
    )
    short = text_field(
        "short_text",
        type_definition=ShortTextNodeDataVO(
            ManualValueDefinitionVO(),
            locale=LocaleCodeVO("uk"),
            fallback_policy=LocaleFallbackPolicyVO(
                LocaleFallbackMode.LOCALE_CHAIN, (LocaleCodeVO("ru"),)
            ),
            transforms=(TransformDefinitionVO(TransformOperation.STRING_TRIM),),
        ),
    )
    long = text_field(
        "long_text",
        type_definition=LongTextNodeDataVO(
            ManualValueDefinitionVO(),
            transforms=(
                TransformDefinitionVO(
                    TransformOperation.STRING_TRUNCATE, TruncateParametersVO(1000)
                ),
            ),
        ),
    )
    sku = text_field("sku")
    price = money_field(calculation)
    price = replace(
        price,
        type_definition=replace(
            price.type_definition,
            currency=None,
            transforms=(
                TransformDefinitionVO(
                    TransformOperation.MONEY_CEIL_STEP,
                    MoneyCeilStepParametersVO(Decimal("0.000001")),
                ),
            ),
        ),
    )
    return feed(FeedSchemaVO((short, long, sku, price)))


class FeedCrudDomainTests(unittest.TestCase):
    """Проверяет атомарное поведение неизменяемого корня."""

    def test_settings_change_preserves_schema_and_increments_once(self) -> None:
        """Несколько новых настроек образуют одно состояние и одну следующую версию."""
        original = rich_feed()
        xml = FeedExportSettingsVO(
            XmlExportSettingsVO(root_name=ExportNameVO("offers"))
        )
        result = original.change_settings(
            name=FeedNameVO("Новое имя"),
            code=FeedCodeVO("new-code"),
            export_settings=xml,
            now=NOW + timedelta(seconds=1),
        )
        self.assertEqual(result.id, original.id)
        self.assertEqual(result.created_at, original.created_at)
        self.assertEqual(result.schema, original.schema)
        self.assertEqual(result.version, FeedVersionVO(2))
        self.assertEqual(original.version, FeedVersionVO(1))
        self.assertEqual(original.name, FeedNameVO("Партнёрский"))
        self.assertEqual(result.export_settings, xml)
        self.assertEqual(result.updated_at, NOW + timedelta(seconds=1))

    def test_noop_and_archive_are_idempotent(self) -> None:
        """Повтор сохранения/архивации не меняет дату и версию."""
        original = rich_feed()
        unchanged = original.change_settings(
            name=original.name,
            code=original.code,
            export_settings=original.export_settings,
            now=NOW + timedelta(seconds=1),
        )
        self.assertIs(unchanged, original)
        archived = original.archive(now=NOW + timedelta(seconds=2))
        self.assertEqual(archived.status, FeedStatus.ARCHIVED)
        self.assertEqual(archived.version.value, 2)
        self.assertEqual(archived.schema, original.schema)
        self.assertIs(archived.archive(now=NOW + timedelta(days=1)), archived)
        with self.assertRaises(FeedArchivedError):
            archived.change_settings(
                name=archived.name,
                code=archived.code,
                export_settings=archived.export_settings,
                now=NOW + timedelta(seconds=3),
            )

    def test_invalid_change_leaves_original_untouched(self) -> None:
        """Неверные время и свойства не обходят фабрику и не меняют источник."""
        original = rich_feed()
        saved = FeedMapper.to_insert_values(original)
        for changes in (
            {"name": "raw"},
            {"code": None},
            {"export_settings": {}},
            {"now": NOW.replace(tzinfo=None)},
            {"now": NOW - timedelta(seconds=1)},
        ):
            with (
                self.subTest(changes=changes),
                self.assertRaises(InvalidFeedValueError),
            ):
                original.change_settings(
                    **(
                        dict(
                            name=original.name,
                            code=original.code,
                            export_settings=original.export_settings,
                            now=NOW,
                        )
                        | changes
                    )
                )
            self.assertEqual(FeedMapper.to_insert_values(original), saved)
        for value in (NOW.replace(tzinfo=None), NOW - timedelta(seconds=1)):
            with self.assertRaises(InvalidFeedValueError):
                original.archive(now=value)

    def test_version_is_typed_bounded_and_restored(self) -> None:
        """Версия сохранения не принимает bool или значения вне BIGINT."""
        for value in (0, -1, True, 1.0, "1", 9223372036854775808):
            with self.subTest(value=value), self.assertRaises(InvalidFeedValueError):
                FeedVersionVO(value)
        original = rich_feed()
        row = FeedMapper.to_insert_values(original)
        row["row_version"] = 7
        restored = FeedMapper.to_domain(row)
        self.assertEqual(restored.version, FeedVersionVO(7))
        self.assertEqual(restored.archive(now=NOW).version, FeedVersionVO(8))


class FeedCrudMapperTests(unittest.TestCase):
    """Проверяет сохранение определений без потери данных и исполнения формул."""

    def test_access_mode_is_read_and_written_inside_feed_settings(self) -> None:
        """Старый документ публичен, а явный испорченный режим отклоняется."""
        original = feed()
        private = original.change_access_mode(FeedAccessMode.PRIVATE, now=NOW)
        row = FeedMapper.to_insert_values(private)
        self.assertNotIn("access_mode", row)
        settings = row["export_settings"]
        self.assertEqual(settings["access_mode"], "PRIVATE")
        self.assertEqual(FeedMapper.to_domain(row), private)
        self.assertEqual(
            FeedQueryMapper.to_details(row).export_settings,
            FeedQueryMapper.to_details(
                FeedMapper.to_insert_values(original)
            ).export_settings,
        )
        legacy = {key: value for key, value in settings.items() if key != "access_mode"}
        self.assertEqual(
            FeedMapper.to_domain(row | {"export_settings": legacy}).access_mode,
            FeedAccessMode.PUBLIC,
        )
        for invalid in (None, "unknown", True, ["PUBLIC"]):
            with self.subTest(mode=invalid), self.assertRaises(InvalidFeedStorageError):
                FeedMapper.to_domain(
                    row | {"export_settings": settings | {"access_mode": invalid}}
                )

    def test_complete_schema_round_trip_and_json_serializability(self) -> None:
        """Полная схема сохраняет UUID, Decimal, локали, fallback и все вложенные узлы."""
        original = rich_feed()
        row = FeedMapper.to_insert_values(original)
        row["schema_definition"] = json.loads(json.dumps(row["schema_definition"]))
        row["export_settings"] = json.loads(json.dumps(row["export_settings"]))
        restored = FeedMapper.to_domain(row)
        self.assertEqual(restored, original)
        self.assertIn("40.123456", json.dumps(row["schema_definition"]))
        self.assertIsNone(restored.schema.fields[3].type_definition.currency)
        self.assertEqual(
            restored.schema.fields[3].type_definition.transforms[0].parameters.step,
            Decimal("0.000001"),
        )

    def test_csv_xml_and_empty_schema_round_trip(self) -> None:
        """Один обязательный формат со всеми параметрами сохраняется при пустой схеме."""
        for settings in (
            CsvExportSettingsVO(delimiter=";", include_header=False),
            XmlExportSettingsVO(
                root_name=ExportNameVO("offers"), item_name=ExportNameVO("offer")
            ),
        ):
            original = feed(export_settings=FeedExportSettingsVO(settings))
            self.assertEqual(
                FeedMapper.to_domain(FeedMapper.to_insert_values(original)), original
            )

    def test_text_sources_and_source_manual_money_round_trip(self) -> None:
        """Прямые источники и MANUAL не превращаются в расчёт или другой тип поля."""
        short = text_field(
            "source_title",
            type_definition=ShortTextNodeDataVO(
                SourceValueDefinitionVO(
                    SourceReferenceVO(SourceProvider.CATALOG, CatalogSourcePath.TITLE)
                ),
                locale=LocaleCodeVO("uk"),
                fallback_policy=LocaleFallbackPolicyVO(),
            ),
        )
        long = text_field(
            "source_description",
            type_definition=LongTextNodeDataVO(
                SourceValueDefinitionVO(
                    SourceReferenceVO(
                        SourceProvider.CATALOG, CatalogSourcePath.DESCRIPTION
                    )
                ),
                locale=LocaleCodeVO("ru"),
            ),
        )
        price = money_field()
        manual = replace(
            price,
            type_definition=replace(
                price.type_definition,
                value_definition=MoneyValueDefinitionVO(MoneyValueMode.MANUAL),
                currency=None,
            ),
        )
        for field in (price, manual):
            original = feed(FeedSchemaVO((short, long, field)))
            restored = FeedMapper.to_domain(FeedMapper.to_insert_values(original))
            self.assertEqual(restored, original)

    def test_corrupt_storage_never_becomes_empty_schema_or_csv(self) -> None:
        """Потерянные свойства и неизвестные узлы не восстанавливаются с defaults."""
        original = rich_feed()
        row = FeedMapper.to_insert_values(original)
        for key in row:
            corrupted = {name: value for name, value in row.items() if name != key}
            with self.subTest(missing=key), self.assertRaises(InvalidFeedStorageError):
                FeedMapper.to_domain(corrupted)
        for settings in ({}, {"formats": []}, {"format_settings": {"format": "yaml"}}):
            with (
                self.subTest(settings=settings),
                self.assertRaises(InvalidFeedStorageError),
            ):
                FeedMapper.to_domain(row | {"export_settings": settings})
        document = schema_document(original.schema)
        for changed in (
            {"schema_format_version": 1},
            {"unknown": 1},
            {"root": {}},
        ):
            with (
                self.subTest(changed=changed),
                self.assertRaises(InvalidFeedStorageError),
            ):
                decode_schema(document | changed)
        bad = copy.deepcopy(document)
        bad["fields"][3]["data"]["value"]["calculation"]["default_expression"] = {
            "kind": "python",
            "code": "unsafe",
        }
        with self.assertRaises(InvalidFeedStorageError):
            FeedMapper.to_domain(row | {"schema_definition": bad})
        bad = copy.deepcopy(document)
        bad["fields"][3]["data"]["value"]["calculation"]["default_expression"] = {
            "kind": "decimal",
            "value": 1.234,
        }
        with self.assertRaises(InvalidFeedStorageError):
            FeedMapper.to_domain(row | {"schema_definition": bad})

    def test_reader_limits_depth_and_root_rechecks_duplicates(self) -> None:
        """Парсер ограничивает рекурсию, а уникальность остаётся инвариантом корня."""
        original = rich_feed()
        document = schema_document(original.schema)
        value = {"kind": "decimal", "value": "1"}
        for _ in range(33):
            value = {"kind": "arithmetic", "operator": "NEGATE", "operand": value}
        bad = copy.deepcopy(document)
        bad["fields"][3]["data"]["value"]["calculation"]["default_expression"] = value
        with self.assertRaises(InvalidFeedStorageError):
            decode_schema(bad)
        bad = copy.deepcopy(document)
        bad["fields"].append(copy.deepcopy(bad["fields"][0]))
        row = FeedMapper.to_insert_values(original) | {"schema_definition": bad}
        with self.assertRaises(InvalidFeedStorageError):
            FeedMapper.to_domain(row)

    def test_read_projection_does_not_restore_feed(self) -> None:
        """Карточка строится без восстановления корня агрегата."""
        row = FeedMapper.to_insert_values(rich_feed())
        with patch.object(
            Feed, "restore", side_effect=AssertionError("read restored root")
        ):
            result = FeedQueryMapper.to_details(row)
        self.assertEqual(result.version, 1)
        self.assertEqual(len(result.schema["fields"]), 4)


class FeedCrudApplicationTests(unittest.IsolatedAsyncioTestCase):
    """Проверяет сценарии через контракты, без SQL и HTTP."""

    async def asyncSetUp(self) -> None:
        """Подготавливает явные часы и репозиторий записи."""
        self.original = rich_feed()
        self.repository = SimpleNamespace(
            add=AsyncMock(),
            get_settings_for_update=AsyncMock(
                return_value=LockedFeedSettings(
                    self.original, schema_document(self.original.schema)
                )
            ),
            save_settings=AsyncMock(),
        )
        self.clock = SimpleNamespace(now=Mock(return_value=NOW + timedelta(seconds=1)))

    async def test_create_uses_external_id_and_clock_with_empty_draft(self) -> None:
        """Сценарий не принимает клиентские схему/статус и создаёт полное начальное состояние."""
        identifier = uuid4()
        handler = CreateFeedHandler(
            self.repository, self.clock, SimpleNamespace(new=lambda: identifier)
        )
        result = await handler.execute(
            CreateFeedCommand(
                "Новый фид",
                "new-feed",
                FeedExportSettingsDTO(CsvExportSettingsDTO(delimiter=";")),
            )
        )
        saved = self.repository.add.call_args.args[0]
        self.assertEqual(saved.id.uuid, identifier)
        self.assertEqual(saved.schema.fields, ())
        self.assertEqual(saved.status, FeedStatus.DRAFT)
        self.assertEqual(result.version, 1)
        self.assertEqual(result.schema["fields"], [])
        self.assertEqual(result.export_settings.format_settings.delimiter, ";")

    async def test_patch_preserves_unspecified_properties_and_schema(self) -> None:
        """Изменение имени не теряет схему, код или параметры экспорта."""
        result = await UpdateFeedHandler(self.repository, self.clock).execute(
            UpdateFeedCommand(
                self.original.id,
                1,
                name="Новое имя",
            )
        )
        saved = self.repository.save_settings.call_args.args[0]
        self.assertEqual(saved.schema, self.original.schema)
        self.assertEqual(saved.code, self.original.code)
        self.assertEqual(result.version, 2)
        self.assertEqual(
            self.repository.save_settings.call_args.kwargs["expected_version"],
            FeedVersionVO(1),
        )

    async def test_noop_does_not_save_and_stale_patch_does_not_overwrite(self) -> None:
        """Повтор значения не пишет БД; устаревшая версия отклоняется до изменения."""
        handler = UpdateFeedHandler(self.repository, self.clock)
        result = await handler.execute(
            UpdateFeedCommand(self.original.id, 1, name=self.original.name.value)
        )
        self.assertEqual(result.version, 1)
        self.repository.save_settings.assert_not_awaited()
        with self.assertRaises(FeedVersionConflictError):
            await handler.execute(UpdateFeedCommand(self.original.id, 2, name="Другой"))
        self.repository.save_settings.assert_not_awaited()
        with self.assertRaises(InvalidFeedValueError):
            await handler.execute(UpdateFeedCommand(self.original.id, 1))

    async def test_archive_and_repeated_delete(self) -> None:
        """Архивация сохраняет агрегат, повторный DELETE не увеличивает версию."""
        handler = ArchiveFeedHandler(self.repository, self.clock)
        await handler.execute(ArchiveFeedCommand(self.original.id, 1))
        archived = self.repository.save_settings.call_args.args[0]
        self.assertEqual(archived.status, FeedStatus.ARCHIVED)
        self.assertEqual(archived.version.value, 2)
        self.repository.get_settings_for_update.return_value = LockedFeedSettings(
            archived, schema_document(archived.schema)
        )
        self.repository.save_settings.reset_mock()
        await handler.execute(ArchiveFeedCommand(self.original.id, 1))
        self.repository.save_settings.assert_not_awaited()

    async def test_missing_query_and_invalid_page(self) -> None:
        """Чтение не подменяет отсутствие и не отправляет неверную страницу в SQL."""
        query_repository = SimpleNamespace(
            get_details=AsyncMock(return_value=None), list=AsyncMock()
        )
        with self.assertRaises(FeedNotFoundError):
            await GetFeedHandler(query_repository).execute(
                GetFeedQuery(self.original.id)
            )
        for query in (
            ListFeedsQuery(limit=0),
            ListFeedsQuery(limit=101),
            ListFeedsQuery(offset=-1),
            ListFeedsQuery(status="unknown"),
            ListFeedsQuery(search="a" * 256),
        ):
            with self.subTest(query=query), self.assertRaises(InvalidFeedValueError):
                await ListFeedsHandler(query_repository).execute(query)
        query_repository.list.assert_not_awaited()


class FeedCrudRequestTests(unittest.TestCase):
    """Проверяет транспортные различия missing/null и закрытые форматы."""

    def test_create_requires_one_format_and_rejects_schema_and_status(self) -> None:
        """Клиент задаёт настройки; пустая схема и DRAFT принадлежат Domain."""
        payload = {
            "name": "Фид",
            "code": "feed",
            "export_settings": {"format_settings": {"format": "csv"}},
        }
        valid = CreateFeedRequest.model_validate(payload)
        self.assertEqual(valid.export_settings.to_dto().format_settings.format, "csv")
        for change in (
            {"export_settings": None},
            {"export_settings": {}},
            {"export_settings": {"format_settings": {"format": "yaml"}}},
            {"schema": {}},
            {"status": "ACTIVE"},
            {
                "export_settings": {
                    "format_settings": {"format": "csv", "root_name": "catalog"}
                }
            },
            {"export_settings": {"formats": []}},
        ):
            with self.subTest(change=change), self.assertRaises(ValidationError):
                CreateFeedRequest.model_validate(payload | change)

    def test_patch_rejects_empty_null_and_invalid_versions(self) -> None:
        """Пропущенные свойства остаются отсутствующими; null не становится сбросом."""
        valid = PatchFeedRequest.model_validate(
            {"expected_version": 1, "name": "Новое"}
        )
        self.assertEqual(valid.model_fields_set, {"expected_version", "name"})
        for payload in (
            {"expected_version": 1},
            {"name": "Новое"},
            {"expected_version": 1, "name": None},
            {"expected_version": 1, "code": None},
            {"expected_version": 1, "export_settings": None},
            {"expected_version": True, "name": "Новое"},
            {"expected_version": 0, "name": "Новое"},
            {"expected_version": 1, "schema": {}},
        ):
            with self.subTest(payload=payload), self.assertRaises(ValidationError):
                PatchFeedRequest.model_validate(payload)


if __name__ == "__main__":
    unittest.main()
