"""Объекты Feed и структурные инварианты без вычисления цен или внешних сервисов."""

from dataclasses import FrozenInstanceError, fields, replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal, Inexact, Rounded, localcontext
from enum import StrEnum
from uuid import uuid4
import unittest

from src.modules.shared.domain.domain_error import DomainError
from src.modules.shared.domain.value_object.currency import CurrencyVO
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.feed_builder.domain.feed.aggregate import Feed
from src.modules.feed_builder.domain.feed.entity.field_node import FieldNodeDefinition
from src.modules.feed_builder.domain.feed.expression.entity.conditional_price_rule import (
    ConditionalPriceRule,
)
from src.modules.feed_builder.domain.feed.expression.enum.arithmetic_operator import (
    ArithmeticOperator,
)
from src.modules.feed_builder.domain.feed.expression.enum.comparison_operator import (
    ComparisonOperator,
)
from src.modules.feed_builder.domain.feed.enum.catalog_source_path import (
    CatalogSourcePath,
)
from src.modules.feed_builder.domain.feed.enum.source_provider import SourceProvider
from src.modules.feed_builder.domain.feed.enum.export_format import ExportFormat
from src.modules.feed_builder.domain.feed.enum.feed_status import FeedStatus
from src.modules.feed_builder.domain.feed.enum.feed_product_mode import FeedProductMode
from src.modules.feed_builder.domain.feed.enum.field_value_type import FieldValueType
from src.modules.feed_builder.domain.feed.expression.enum.literal_value_type import (
    LiteralValueType,
)
from src.modules.feed_builder.domain.feed.enum.locale_fallback_mode import (
    LocaleFallbackMode,
)
from src.modules.feed_builder.domain.feed.expression.enum.logical_operator import LogicalOperator
from src.modules.feed_builder.domain.feed.enum.money_value_mode import MoneyValueMode
from src.modules.feed_builder.domain.feed.expression.enum.presence_operator import PresenceOperator
from src.modules.feed_builder.domain.feed.expression.enum.price_function import PriceFunction
from src.modules.feed_builder.domain.feed.enum.transform_operation import (
    TransformOperation,
)
from src.modules.feed_builder.domain.feed.error import (
    DefinitionStructureLimitExceededError,
    DuplicateExportNameError,
    DuplicateFieldIdentifierError,
    DuplicateFieldKeyError,
    DuplicatePriceRuleIdentifierError,
    InvalidFeedValueError,
    InvalidFieldDefinitionError,
    InvalidPriceCalculationDefinitionError,
)
from src.modules.feed_builder.domain.feed.limits import (
    MAX_AST_DEPTH,
    MAX_AST_NODES,
    MAX_FIELDS,
    MAX_RULES,
    MAX_TRANSFORMS,
)
from src.modules.feed_builder.domain.feed.types import Condition, Expression
from src.modules.feed_builder.domain.feed.expression.structure_policy import (
    PriceCalculationStructurePolicy,
)
from src.modules.feed_builder.domain.feed.expression.value_object.arithmetic_expression import (
    ArithmeticExpressionVO,
)
from src.modules.feed_builder.domain.feed.expression.value_object.collection_literal import (
    CollectionLiteralVO,
)
from src.modules.feed_builder.domain.feed.expression.value_object.comparison_condition import (
    ComparisonConditionVO,
)
from src.modules.feed_builder.domain.feed.value_object.csv_export_settings import (
    CsvExportSettingsVO,
)
from src.modules.feed_builder.domain.feed.expression.value_object.decimal_literal import (
    DecimalLiteralVO,
)
from src.modules.feed_builder.domain.feed.value_object.export_name import ExportNameVO
from src.modules.feed_builder.domain.feed.value_object.feed_code import FeedCodeVO
from src.modules.feed_builder.domain.feed.value_object.feed_export_settings import (
    FeedExportSettingsVO,
)
from src.modules.feed_builder.domain.feed.value_object.feed_id import FeedIdVO
from src.modules.feed_builder.domain.feed.value_object.feed_version import FeedVersionVO
from src.modules.feed_builder.domain.feed.value_object.feed_name import FeedNameVO
from src.modules.feed_builder.domain.feed.value_object.feed_schema import FeedSchemaVO
from src.modules.feed_builder.domain.feed.value_object.text_constraints import (
    TextConstraintsVO,
)
from src.modules.feed_builder.domain.feed.value_object.money_constraints import (
    MoneyConstraintsVO,
)
from src.modules.feed_builder.domain.feed.field_node.short_text.value_object.data import (
    ShortTextNodeDataVO,
)
from src.modules.feed_builder.domain.feed.field_node.long_text.value_object.data import (
    LongTextNodeDataVO,
)
from src.modules.feed_builder.domain.feed.field_node.money.value_object.data import (
    MoneyNodeDataVO,
)
from src.modules.feed_builder.domain.feed.value_object.field_export_settings import (
    FieldExportSettingsVO,
)
from src.modules.feed_builder.domain.feed.value_object.field_id import FieldIdVO
from src.modules.feed_builder.domain.feed.value_object.field_key import FieldKeyVO
from src.modules.feed_builder.domain.feed.value_object.field_label import FieldLabelVO
from src.modules.feed_builder.domain.feed.expression.value_object.function_expression import (
    FunctionExpressionVO,
)
from src.modules.feed_builder.domain.feed.value_object.locale_code import LocaleCodeVO
from src.modules.feed_builder.domain.feed.value_object.locale_fallback_policy import (
    LocaleFallbackPolicyVO,
)
from src.modules.feed_builder.domain.feed.expression.value_object.logical_condition import (
    LogicalConditionVO,
)
from src.modules.feed_builder.domain.feed.value_object.manual_value_definition import (
    ManualValueDefinitionVO,
)
from src.modules.feed_builder.domain.feed.value_object.money_ceil_step_parameters import (
    MoneyCeilStepParametersVO,
)
from src.modules.feed_builder.domain.feed.value_object.price_amount import PriceAmountVO
from src.modules.feed_builder.domain.feed.value_object.money_value_definition import (
    MoneyValueDefinitionVO,
)
from src.modules.feed_builder.domain.feed.expression.value_object.parameter_reference import (
    ParameterReferenceVO,
)
from src.modules.feed_builder.domain.feed.expression.value_object.presence_condition import (
    PresenceConditionVO,
)
from src.modules.feed_builder.domain.feed.expression.value_object.price_calculation import (
    PriceCalculationVO,
)
from src.modules.feed_builder.domain.feed.expression.value_object.price_rule_id import (
    PriceRuleIdVO,
)
from src.modules.feed_builder.domain.feed.expression.value_object.purchase_price_source import (
    PurchasePriceSourceVO,
)
from src.modules.feed_builder.domain.feed.expression.value_object.scalar_literal import (
    ScalarLiteralVO,
)
from src.modules.feed_builder.domain.feed.value_object.source_reference import (
    SourceReferenceVO,
)
from src.modules.feed_builder.domain.feed.value_object.source_value_definition import (
    SourceValueDefinitionVO,
)
from src.modules.feed_builder.domain.feed.value_object.transform_definition import (
    TransformDefinitionVO,
)
from src.modules.feed_builder.domain.feed.value_object.truncate_parameters import (
    TruncateParametersVO,
)
from src.modules.feed_builder.domain.feed.value_object.xml_export_settings import (
    XmlExportSettingsVO,
)

NOW = datetime(2026, 11, 20, 10, tzinfo=UTC)
UAH = CurrencyVO("UAH")


def text_field(name: str = "custom_name", **changes: object) -> FieldNodeDefinition:
    """Создаёт произвольное ручное поле без привилегированных ключей."""
    values = dict(
        identifier=FieldIdVO(uuid4()),
        key=FieldKeyVO(name),
        label=FieldLabelVO(name),
        type_definition=ShortTextNodeDataVO(ManualValueDefinitionVO()),
        export=FieldExportSettingsVO(ExportNameVO(name)),
    )
    return FieldNodeDefinition.create(**(values | changes))


def money_field(
    calculation: PriceCalculationVO | None = None, **changes: object
) -> FieldNodeDefinition:
    """Создаёт денежное поле с прямым источником либо переданным определением."""
    definition = (
        MoneyValueDefinitionVO(
            MoneyValueMode.SOURCE,
            source=SourceReferenceVO(
                SourceProvider.CATALOG, CatalogSourcePath.REGULAR_PRICE
            ),
        )
        if calculation is None
        else MoneyValueDefinitionVO(MoneyValueMode.CALCULATED, calculation=calculation)
    )
    values = dict(
        identifier=FieldIdVO(uuid4()),
        key=FieldKeyVO("partner_amount"),
        label=FieldLabelVO("Цена партнёра"),
        type_definition=MoneyNodeDataVO(currency=UAH, value_definition=definition),
        export=FieldExportSettingsVO(ExportNameVO("partner_amount")),
    )
    return FieldNodeDefinition.create(**(values | changes))


def feed(schema: FeedSchemaVO | None = None, **changes: object) -> Feed:
    """Создаёт Feed с явными идентификатором и временем."""
    return Feed.create(
        **(
            dict(
                identifier=FeedIdVO(uuid4()),
                name=FeedNameVO("Партнёрский"),
                code=FeedCodeVO("partner"),
                now=NOW,
                schema=schema,
                export_settings=FeedExportSettingsVO(
                    format_settings=CsvExportSettingsVO()
                ),
            )
            | changes
        )
    )


def rule(
    condition: Condition | None = None, expression: Expression | None = None
) -> ConditionalPriceRule:
    """Создаёт условное определение, не получая параметры товара."""
    return ConditionalPriceRule.create(
        identifier=PriceRuleIdVO(uuid4()),
        condition=(
            PresenceConditionVO(
                PresenceOperator.EXISTS, ParameterReferenceVO("price.sale")
            )
            if condition is None
            else condition
        ),
        expression=(
            ParameterReferenceVO("price.sale") if expression is None else expression
        ),
    )


class FeedConstructionTests(unittest.TestCase):
    """Проверяет фабрики, границу агрегата и независимость пользовательских полей."""

    def test_create_assigns_every_field_with_empty_or_explicit_schema(self) -> None:
        """Create сохраняет все поля с обязательным CSV/XML и необязательной схемой."""
        identifier = FeedIdVO(uuid4())
        name = FeedNameVO("Новый пользовательский прайс")
        code = FeedCodeVO("created-feed")
        schema = FeedSchemaVO((text_field(), money_field()))
        for supplied_schema in (None, schema):
            for format_settings in (
                CsvExportSettingsVO(delimiter=";", include_header=False),
                XmlExportSettingsVO(
                    root_name=ExportNameVO("offers"), item_name=ExportNameVO("offer")
                ),
            ):
                with self.subTest(
                    schema=supplied_schema, format_settings=format_settings
                ):
                    settings = FeedExportSettingsVO(format_settings=format_settings)
                    result = Feed.create(
                        identifier=identifier,
                        name=name,
                        code=code,
                        now=NOW,
                        schema=supplied_schema,
                        export_settings=settings,
                    )
                    expected = {
                        "id": identifier,
                        "name": name,
                        "code": code,
                        "status": FeedStatus.DRAFT,
                        "schema": FeedSchemaVO() if supplied_schema is None else schema,
                        "export_settings": settings,
                        "created_at": NOW,
                        "updated_at": NOW,
                        "version": FeedVersionVO(1),
                        "public_link_id": None,
                    }
                    self.assertEqual(
                        {item.name for item in fields(Feed)}, set(expected)
                    )
                    for attribute, value in expected.items():
                        self.assertEqual(getattr(result, attribute), value, attribute)
                    self.assertIs(result.export_settings, settings)
                    self.assertIs(
                        result.export_settings.format_settings, format_settings
                    )
                    self.assertIs(
                        result.export_settings.product_mode,
                        FeedProductMode.VARIABLE_TO_SINGLE,
                    )

    def test_factories_require_explicit_export_settings(self) -> None:
        """Ни create, ни restore не выбирают формат вместо вызывающего кода."""
        common = dict(
            identifier=FeedIdVO(uuid4()),
            name=FeedNameVO("Прайс"),
            code=FeedCodeVO("price"),
        )
        for factory, arguments in (
            (Feed.create, common | {"now": NOW}),
            (
                Feed.restore,
                common
                | {
                    "status": FeedStatus.DRAFT,
                    "schema": FeedSchemaVO(),
                    "created_at": NOW,
                    "updated_at": NOW,
                },
            ),
        ):
            with self.subTest(factory=factory.__name__):
                with self.assertRaisesRegex(TypeError, "export_settings"):
                    factory(**arguments)
                with self.assertRaises(InvalidFeedValueError):
                    factory(**arguments, export_settings=None)

    def test_restore_assigns_every_field_from_independent_saved_values(self) -> None:
        """Restore проверяется без create и сохраняет обе разные даты и настройки."""
        identifier = FeedIdVO(uuid4())
        name = FeedNameVO("Восстановленный прайс")
        code = FeedCodeVO("restored-feed")
        schema = FeedSchemaVO((money_field(), text_field("restored_text")))
        settings = FeedExportSettingsVO(
            product_mode=FeedProductMode.VARIABLE_TO_SINGLE,
            format_settings=CsvExportSettingsVO(delimiter=";", include_header=False),
        )
        created_at = NOW - timedelta(days=10)
        updated_at = NOW + timedelta(hours=3)
        result = Feed.restore(
            identifier=identifier,
            name=name,
            code=code,
            status=FeedStatus.PAUSED,
            schema=schema,
            export_settings=settings,
            created_at=created_at,
            updated_at=updated_at,
        )
        expected = {
            "id": identifier,
            "name": name,
            "code": code,
            "status": FeedStatus.PAUSED,
            "schema": schema,
            "export_settings": settings,
            "created_at": created_at,
            "updated_at": updated_at,
            "version": FeedVersionVO(1),
            "public_link_id": None,
        }
        self.assertEqual({item.name for item in fields(Feed)}, set(expected))
        for attribute, value in expected.items():
            self.assertEqual(getattr(result, attribute), value, attribute)
        self.assertIs(result.export_settings, settings)
        self.assertIs(
            result.export_settings.product_mode,
            FeedProductMode.VARIABLE_TO_SINGLE,
        )

    def test_empty_create_has_no_demonstration_fields(self) -> None:
        """Новый Feed имеет пустую схему, DRAFT и явно переданные даты."""
        result = feed()
        self.assertEqual(result.schema.fields, ())
        self.assertEqual(result.status, FeedStatus.DRAFT)
        self.assertEqual((result.created_at, result.updated_at), (NOW, NOW))
        self.assertFalse(hasattr(result, "_events"))
        self.assertFalse(hasattr(result, "pricing_policy_id"))
        self.assertFalse(hasattr(result, "currency"))

    def test_identifiers_preserve_uuid_and_reject_other_entity_types(self) -> None:
        """Типизированные ID не генерируются и не смешиваются при преобразовании."""
        raw = uuid4()
        identifier = FeedIdVO.from_value(str(raw))
        self.assertEqual(identifier.uuid, raw)
        self.assertIs(FeedIdVO.from_value(identifier), identifier)
        for constructor in (FeedIdVO, FieldIdVO, PriceRuleIdVO):
            with self.assertRaises(DomainError):
                constructor(True)
        with self.assertRaises(DomainError):
            FeedIdVO.from_value(FieldIdVO(raw))

    def test_root_rechecks_and_detaches_reconstituted_child_entities(self) -> None:
        """Restore корня не доверяет Entity, собранной в обход её явной фабрики."""
        original = text_field()
        invalid = replace(original, type_definition={})
        with self.assertRaises(InvalidFieldDefinitionError):
            feed(FeedSchemaVO((invalid,)))
        transforms = [TransformDefinitionVO(TransformOperation.STRING_TRIM)]
        reconstituted = replace(
            original,
            type_definition=ShortTextNodeDataVO(
                ManualValueDefinitionVO(), transforms=transforms
            ),
        )
        restored = feed(FeedSchemaVO((reconstituted,)))
        transforms.clear()
        self.assertEqual(len(restored.schema.fields[0].type_definition.transforms), 1)
        self.assertIsInstance(
            restored.schema.fields[0].type_definition.transforms, tuple
        )

    def test_restore_preserves_full_schema_and_identity(self) -> None:
        """Восстановление не меняет ID, порядок правил, значения и timestamps."""
        category_id = EntityIdVO(uuid4())
        category = ComparisonConditionVO(
            ComparisonOperator.CONTAINS,
            ParameterReferenceVO("product.category_ids"),
            ScalarLiteralVO(LiteralValueType.UUID, category_id),
        )
        calculation = PriceCalculationVO(
            default_expression=ParameterReferenceVO("price.regular"),
            rules=[rule(category, ParameterReferenceVO("price.purchase")), rule()],
            purchase_source=PurchasePriceSourceVO(EntityIdVO(uuid4())),
        )
        second = money_field(calculation)
        first = text_field("arbitrary_column")
        original = feed(FeedSchemaVO([first, second]))
        restored = Feed.restore(
            identifier=original.id,
            name=original.name,
            code=original.code,
            status=FeedStatus.PAUSED,
            schema=original.schema,
            export_settings=original.export_settings,
            created_at=NOW,
            updated_at=NOW + timedelta(days=1),
        )
        self.assertEqual(restored.id, original.id)
        self.assertEqual(restored.schema, original.schema)
        self.assertEqual(
            [item.id for item in restored.schema.fields], [first.id, second.id]
        )
        self.assertEqual(
            restored.schema.fields[
                1
            ].type_definition.value_definition.calculation.rules,
            calculation.rules,
        )
        self.assertEqual(restored.status, FeedStatus.PAUSED)
        self.assertEqual(restored.updated_at, NOW + timedelta(days=1))

    def test_field_and_rule_restore_preserve_identifiers(self) -> None:
        """Entity восстанавливаются без генерации новой идентичности и скрытых defaults."""
        source = text_field(
            type_definition=ShortTextNodeDataVO(
                ManualValueDefinitionVO(),
                locale=LocaleCodeVO("uk"),
                constraints=TextConstraintsVO(required=True),
            ),
            ai_instruction="Будущий контекст",
        )
        restored = FieldNodeDefinition.restore(
            identifier=source.id,
            **{
                item.name: getattr(source, item.name)
                for item in fields(source)
                if item.name != "id"
            },
        )
        self.assertEqual(restored, source)
        original_rule = rule()
        self.assertEqual(
            ConditionalPriceRule.restore(
                identifier=original_rule.id,
                condition=original_rule.condition,
                expression=original_rule.expression,
            ),
            original_rule,
        )

    def test_all_names_are_equal_and_required_does_not_seed_fields(self) -> None:
        """Особые на вид имена не меняют состав и возможности схемы."""
        for name in ("title", "description", "currency", "price", "anything"):
            with self.subTest(name=name):
                field = text_field(
                    name,
                    type_definition=ShortTextNodeDataVO(
                        ManualValueDefinitionVO(),
                        constraints=TextConstraintsVO(required=True),
                    ),
                )
                self.assertEqual(feed(FeedSchemaVO((field,))).schema.fields, (field,))
                self.assertFalse(hasattr(field, "system_role"))
        self.assertEqual(feed().schema.fields, ())

    def test_duplicate_identifiers_keys_and_export_names_are_root_errors(self) -> None:
        """Корень владеет уникальностью полного состава, включая неэкспортируемые поля."""
        original = text_field()
        cases = [
            (
                text_field("other", identifier=original.id),
                DuplicateFieldIdentifierError,
            ),
            (text_field("other", key=original.key), DuplicateFieldKeyError),
            (
                text_field(
                    "other",
                    export=FieldExportSettingsVO(original.export.name, enabled=False),
                ),
                DuplicateExportNameError,
            ),
        ]
        for duplicate, error in cases:
            with self.subTest(error=error.__name__), self.assertRaises(error) as caught:
                feed(FeedSchemaVO((original, duplicate)))
            self.assertEqual(caught.exception.path[:3], ("schema", "fields", 1))
        self.assertEqual(original.key, FieldKeyVO("custom_name"))

    def test_invalid_root_types_dates_and_version_are_rejected(self) -> None:
        """Не принимает чужие ID, dict вместо VO, naive/обратные даты и bool-версию."""
        for changes in (
            {"identifier": FieldIdVO(uuid4())},
            {"name": "plain"},
            {"schema": {}},
            {"export_settings": {}},
            {"now": NOW.replace(tzinfo=None)},
        ):
            with (
                self.subTest(changes=changes),
                self.assertRaises(InvalidFeedValueError),
            ):
                feed(**changes)
        original = feed()
        for created, updated in (
            (NOW, NOW - timedelta(seconds=1)),
            (NOW, NOW.replace(tzinfo=None)),
        ):
            with self.assertRaises(InvalidFeedValueError):
                Feed.restore(
                    identifier=original.id,
                    name=original.name,
                    code=original.code,
                    status=FeedStatus.DRAFT,
                    schema=original.schema,
                    export_settings=original.export_settings,
                    created_at=created,
                    updated_at=updated,
                )
        for version in (True, 0, 3):
            with self.assertRaises(InvalidFeedValueError):
                FeedSchemaVO(schema_format_version=version)

    def test_deep_immutability_and_input_collections_are_detached(self) -> None:
        """Изменение входных списков не меняет Feed, дерево, transforms и settings."""
        transforms = [TransformDefinitionVO(TransformOperation.STRING_TRIM)]
        arguments = [
            ParameterReferenceVO("price.regular"),
            DecimalLiteralVO(Decimal("1")),
        ]
        expression = FunctionExpressionVO(PriceFunction.MAX, arguments)
        rules = [rule()]
        calculation = PriceCalculationVO(expression, rules)
        schema_fields = [
            text_field(
                type_definition=ShortTextNodeDataVO(
                    ManualValueDefinitionVO(), transforms=transforms
                )
            ),
            money_field(calculation),
        ]
        result = feed(
            FeedSchemaVO(schema_fields),
            export_settings=FeedExportSettingsVO(format_settings=XmlExportSettingsVO()),
        )
        transforms.clear()
        arguments.clear()
        rules.clear()
        schema_fields.clear()
        self.assertEqual(len(result.schema.fields), 2)
        self.assertEqual(len(result.schema.fields[0].type_definition.transforms), 1)
        self.assertEqual(len(calculation.rules), 1)
        self.assertEqual(len(expression.arguments), 2)
        self.assertEqual(result.export_settings.format_settings, XmlExportSettingsVO())
        for value, attribute, new_value in (
            (result, "name", FeedNameVO("Другое")),
            (result.schema.fields[0], "label", FieldLabelVO("Другое")),
            (calculation.rules[0], "expression", DecimalLiteralVO(Decimal("0"))),
            (expression, "arguments", ()),
        ):
            with (
                self.subTest(value=type(value).__name__),
                self.assertRaises(FrozenInstanceError),
            ):
                setattr(value, attribute, new_value)

    def test_configuration_equality_includes_contents_not_only_entity_id(self) -> None:
        """Одинаковые ID не скрывают отличие label или выражения версии определения."""
        original = text_field()
        changed = text_field(identifier=original.id, label=FieldLabelVO("Новое"))
        self.assertNotEqual(FeedSchemaVO((original,)), FeedSchemaVO((changed,)))
        original_rule = rule()
        changed_rule = ConditionalPriceRule.restore(
            identifier=original_rule.id,
            condition=original_rule.condition,
            expression=ParameterReferenceVO("price.regular"),
        )
        self.assertNotEqual(original_rule, changed_rule)


class FeedValuesTests(unittest.TestCase):
    """Проверяет локальные значения, типы и совместимость конфигураций."""

    def test_known_catalog_sources_are_typed_immutable_references(self) -> None:
        """Принимает закрытый набор путей с прежними строковыми кодами без чтения Catalog."""
        for path, code in (
            (CatalogSourcePath.TITLE, "item.title"),
            (CatalogSourcePath.DESCRIPTION, "item.description"),
            (CatalogSourcePath.SKU, "item.sku"),
            (CatalogSourcePath.REGULAR_PRICE, "item.regular_price"),
        ):
            with self.subTest(path=path):
                reference = SourceReferenceVO(SourceProvider.CATALOG, path)
                self.assertIs(reference.provider, SourceProvider.CATALOG)
                self.assertIs(reference.path, path)
                self.assertEqual(reference.provider.value, "catalog")
                self.assertEqual(reference.path.value, code)
                self.assertEqual(reference, SourceReferenceVO(reference.provider, path))
                with self.assertRaises(FrozenInstanceError):
                    reference.path = CatalogSourcePath.TITLE

    def test_sources_reject_raw_values_and_foreign_enums(self) -> None:
        """Даже равные по строковому коду чужие Enum не подменяют контракт источника."""

        class ForeignProvider(StrEnum):
            """Имитирует посторонний Enum с совпадающим кодом провайдера."""

            CATALOG = "catalog"

        class ForeignPath(StrEnum):
            """Имитирует посторонний Enum с совпадающим кодом пути."""

            TITLE = "item.title"

        for provider in (
            "catalog",
            "custom_provider",
            "supplier_sourcing",
            "https://bad",
            ForeignProvider.CATALOG,
            CatalogSourcePath.TITLE,
            None,
            True,
            1,
            {},
        ):
            with (
                self.subTest(provider=provider),
                self.assertRaises(InvalidFeedValueError),
            ):
                SourceReferenceVO(provider, CatalogSourcePath.TITLE)
        for path in (
            "item.title",
            "item.custom_attribute",
            "item.unknown_field",
            "__import__(os)",
            "item[0]",
            "https://url",
            ForeignPath.TITLE,
            SourceProvider.CATALOG,
            None,
            True,
            1,
            {},
        ):
            with self.subTest(path=path), self.assertRaises(InvalidFeedValueError):
                SourceReferenceVO(SourceProvider.CATALOG, path)

    def test_catalog_sources_survive_field_and_feed_factories(self) -> None:
        """Схема четырёх полей сохраняет типизированные источники при create/restore."""
        expected_paths = (
            CatalogSourcePath.TITLE,
            CatalogSourcePath.DESCRIPTION,
            CatalogSourcePath.SKU,
            CatalogSourcePath.REGULAR_PRICE,
        )
        definitions = (
            text_field(
                "title",
                type_definition=ShortTextNodeDataVO(
                    SourceValueDefinitionVO(
                        SourceReferenceVO(
                            SourceProvider.CATALOG, CatalogSourcePath.TITLE
                        )
                    ),
                    locale=LocaleCodeVO("uk"),
                ),
            ),
            text_field(
                "description",
                type_definition=LongTextNodeDataVO(
                    SourceValueDefinitionVO(
                        SourceReferenceVO(
                            SourceProvider.CATALOG, CatalogSourcePath.DESCRIPTION
                        )
                    ),
                    locale=LocaleCodeVO("uk"),
                ),
            ),
            text_field(
                "sku",
                type_definition=ShortTextNodeDataVO(
                    SourceValueDefinitionVO(
                        SourceReferenceVO(SourceProvider.CATALOG, CatalogSourcePath.SKU)
                    ),
                ),
            ),
            money_field(),
        )
        restored_fields = tuple(
            FieldNodeDefinition.restore(
                identifier=definition.id,
                key=definition.key,
                label=definition.label,
                type_definition=definition.type_definition,
                export=definition.export,
                ai_instruction=definition.ai_instruction,
            )
            for definition in definitions
        )
        created = feed(FeedSchemaVO(restored_fields))
        restored = Feed.restore(
            identifier=created.id,
            name=created.name,
            code=created.code,
            status=created.status,
            schema=created.schema,
            export_settings=created.export_settings,
            created_at=created.created_at,
            updated_at=created.updated_at,
        )
        self.assertEqual(restored, created)
        self.assertEqual(restored.schema.fields, definitions)
        for result in (created, restored):
            for definition, path in zip(
                result.schema.fields, expected_paths, strict=True
            ):
                reference = definition.type_definition.value_definition.source
                self.assertIs(reference.provider, SourceProvider.CATALOG)
                self.assertIs(reference.path, path)
        self.assertIsNone(restored.schema.fields[2].type_definition.locale)
        self.assertEqual(restored.schema.fields[3].type_definition.currency, UAH)

    def test_names_and_locales_have_no_external_lookup(self) -> None:
        """Нормализует значения без обращения к внешним справочникам."""
        self.assertEqual(FeedNameVO("  Название  ").value, "Название")
        self.assertEqual(LocaleCodeVO("EN-latn-us").value, "en-Latn-US")
        self.assertEqual(LocaleCodeVO("x-PRIVATE").value, "x-private")
        for constructor, value in (
            (FeedNameVO, ""),
            (FeedNameVO, "x\nname"),
            (FeedCodeVO, "../feed"),
            (FieldKeyVO, "a b"),
            (ExportNameVO, "ns:name"),
            (ExportNameVO, "1bad"),
            (LocaleCodeVO, "en_US"),
            (LocaleCodeVO, "x"),
        ):
            with (
                self.subTest(constructor=constructor.__name__, value=value),
                self.assertRaises(InvalidFeedValueError),
            ):
                constructor(value)

    def test_decimal_constraints_do_not_round_or_accept_float(self) -> None:
        """Сохраняет шесть разрядов под строгим ambient context без исполнения арифметики."""
        amount = Decimal("123.123456")
        with localcontext() as context:
            context.prec = 2
            context.traps[Inexact] = True
            context.traps[Rounded] = True
            self.assertEqual(PriceAmountVO(amount).amount, amount)
            self.assertEqual(DecimalLiteralVO(amount).value, amount)
            self.assertEqual(
                MoneyCeilStepParametersVO(Decimal("0.000001")).step, Decimal("0.000001")
            )
            self.assertEqual(MoneyConstraintsVO(min_amount=amount).min_amount, amount)
        for bad in (
            1.2,
            True,
            "1.2",
            Decimal("NaN"),
            Decimal("Infinity"),
            Decimal("sNaN"),
            Decimal("1e129"),
        ):
            with self.subTest(bad=bad), self.assertRaises(InvalidFeedValueError):
                DecimalLiteralVO(bad)
            with self.subTest(bad=bad), self.assertRaises(InvalidFeedValueError):
                PriceAmountVO(bad)
        for constructor, constraints in (
            (TextConstraintsVO, {"required": 1}),
            (TextConstraintsVO, {"min_length": True}),
            (TextConstraintsVO, {"max_length": -1}),
            (TextConstraintsVO, {"min_length": 2, "max_length": 1}),
            (MoneyConstraintsVO, {"required": 1}),
            (
                MoneyConstraintsVO,
                {"min_amount": Decimal("2"), "max_amount": Decimal("1")},
            ),
            (MoneyConstraintsVO, {"min_amount": 0.1}),
            (MoneyConstraintsVO, {"max_amount": Decimal("NaN")}),
        ):
            with (
                self.subTest(constructor=constructor, constraints=constraints),
                self.assertRaises(InvalidFeedValueError),
            ):
                constructor(**constraints)
        self.assertEqual(TextConstraintsVO(min_length=0, max_length=0).max_length, 0)
        with self.assertRaises(TypeError):
            TextConstraintsVO(min_amount=Decimal("1"))
        with self.assertRaises(TypeError):
            MoneyConstraintsVO(min_length=1)

    def test_transform_parameters_are_typed_and_operations_not_executed(self) -> None:
        """Принимает определения и отвергает неверную пару операции/параметров."""
        self.assertEqual(
            TransformDefinitionVO(
                TransformOperation.STRING_TRUNCATE, TruncateParametersVO(0)
            ).parameters.max_length,
            0,
        )
        for operation, parameters in (
            (TransformOperation.STRING_TRIM, TruncateParametersVO(1)),
            (TransformOperation.MONEY_CEIL_STEP, None),
            (TransformOperation.STRING_TRUNCATE, {}),
            ("string.trim", None),
        ):
            with self.assertRaises(InvalidFeedValueError):
                TransformDefinitionVO(operation, parameters)
        for step in (Decimal("0"), Decimal("-0.1"), Decimal("NaN"), 0.1):
            with self.assertRaises(InvalidFeedValueError):
                MoneyCeilStepParametersVO(step)
        with self.assertRaises(InvalidFeedValueError):
            TruncateParametersVO(True)

    def test_type_settings_reject_incompatible_definitions_and_operations(self) -> None:
        """Каждый тип принимает только свои значения, ограничения и преобразования."""
        for constructor in (ShortTextNodeDataVO, LongTextNodeDataVO):
            for changes in (
                {"constraints": MoneyConstraintsVO(min_amount=Decimal("0"))},
                {
                    "transforms": (
                        TransformDefinitionVO(
                            TransformOperation.MONEY_CEIL_STEP,
                            MoneyCeilStepParametersVO(Decimal("1")),
                        ),
                    )
                },
                {"value_definition": MoneyValueDefinitionVO(MoneyValueMode.MANUAL)},
                {"locale": "uk"},
                {"fallback_policy": {}},
            ):
                with (
                    self.subTest(constructor=constructor, changes=changes),
                    self.assertRaises(InvalidFieldDefinitionError),
                ):
                    constructor(
                        **({"value_definition": ManualValueDefinitionVO()} | changes)
                    )
            with self.assertRaises(TypeError):
                constructor(ManualValueDefinitionVO(), currency=UAH)
        for changes in (
            {"currency": "UAH"},
            {"constraints": TextConstraintsVO(max_length=1)},
            {"transforms": (TransformDefinitionVO(TransformOperation.STRING_TRIM),)},
            {"value_definition": ManualValueDefinitionVO()},
        ):
            with (
                self.subTest(changes=changes),
                self.assertRaises(InvalidFieldDefinitionError),
            ):
                MoneyNodeDataVO(
                    **(
                        {
                            "currency": UAH,
                            "value_definition": MoneyValueDefinitionVO(
                                MoneyValueMode.MANUAL
                            ),
                        }
                        | changes
                    )
                )
        for forbidden in (
            {"locale": LocaleCodeVO("uk")},
            {"fallback_policy": LocaleFallbackPolicyVO()},
        ):
            with self.assertRaises(TypeError):
                MoneyNodeDataVO(
                    currency=UAH,
                    value_definition=MoneyValueDefinitionVO(MoneyValueMode.MANUAL),
                    **forbidden,
                )
        self.assertIsNone(
            MoneyNodeDataVO(
                value_definition=MoneyValueDefinitionVO(MoneyValueMode.MANUAL)
            ).currency
        )

    def test_field_owns_common_properties_and_a_single_closed_type_definition(
        self,
    ) -> None:
        """Тип и его настройки не дублируются в Entity, kind определяется классом VO."""
        original = text_field("sku")
        self.assertEqual(
            {item.name for item in fields(original)},
            {"id", "key", "label", "type_definition", "export", "ai_instruction", "category_tree_id"},
        )
        self.assertIsNone(original.type_definition.locale)
        for name in (
            "value_type",
            "locale",
            "currency",
            "constraints",
            "transforms",
            "fallback_policy",
            "value_definition",
        ):
            self.assertFalse(hasattr(original, name))
            with self.assertRaises(TypeError):
                text_field(**{name: None})
        for invalid in ({}, FieldValueType.STRING, ManualValueDefinitionVO(), None):
            with (
                self.subTest(invalid=invalid),
                self.assertRaises(InvalidFieldDefinitionError),
            ):
                text_field(type_definition=invalid)
        for constructor in (ShortTextNodeDataVO, LongTextNodeDataVO):
            with self.assertRaisesRegex(TypeError, "kind"):
                constructor(ManualValueDefinitionVO(), kind=FieldValueType.MONEY)
        with self.assertRaisesRegex(TypeError, "kind"):
            MoneyNodeDataVO(
                currency=UAH,
                value_definition=MoneyValueDefinitionVO(MoneyValueMode.MANUAL),
                kind=FieldValueType.STRING,
            )

    def test_all_type_variants_survive_field_and_feed_factories(self) -> None:
        """Create и restore сохраняют полный состав каждого типа без потери порядка/ID."""
        fallback = LocaleFallbackPolicyVO(
            LocaleFallbackMode.LOCALE_CHAIN, (LocaleCodeVO("ru"),)
        )
        source = SourceValueDefinitionVO(
            SourceReferenceVO(SourceProvider.CATALOG, CatalogSourcePath.TITLE)
        )
        variants = (
            ShortTextNodeDataVO(
                source,
                TextConstraintsVO(True, 1, 100),
                LocaleCodeVO("uk"),
                fallback,
                (TransformDefinitionVO(TransformOperation.STRING_TRIM),),
            ),
            LongTextNodeDataVO(
                ManualValueDefinitionVO(),
                TextConstraintsVO(False, 0, 5000),
                LocaleCodeVO("uk"),
                fallback,
                (
                    TransformDefinitionVO(
                        TransformOperation.STRING_TRUNCATE, TruncateParametersVO(5000)
                    ),
                ),
            ),
            MoneyNodeDataVO(
                currency=UAH,
                value_definition=MoneyValueDefinitionVO(MoneyValueMode.MANUAL),
                constraints=MoneyConstraintsVO(True, Decimal("0"), Decimal("1000")),
                transforms=(
                    TransformDefinitionVO(
                        TransformOperation.MONEY_CEIL_STEP,
                        MoneyCeilStepParametersVO(Decimal("0.01")),
                    ),
                ),
            ),
        )
        definitions = []
        for index, (variant, kind) in enumerate(
            zip(
                variants,
                (FieldValueType.STRING, FieldValueType.TEXT, FieldValueType.MONEY),
                strict=True,
            )
        ):
            created = text_field(
                f"field_{index}",
                type_definition=variant,
                ai_instruction="Пример метаданных",
            )
            restored = FieldNodeDefinition.restore(
                identifier=created.id,
                **{
                    item.name: getattr(created, item.name)
                    for item in fields(created)
                    if item.name != "id"
                },
            )
            self.assertEqual(restored, created)
            self.assertIsInstance(restored.type_definition, type(variant))
            self.assertEqual(restored.type_definition.kind, kind)
            self.assertEqual(restored.type_definition, variant)
            with self.assertRaises(FrozenInstanceError):
                restored.type_definition.constraints = None
            definitions.append(restored)
        original = feed(FeedSchemaVO(definitions))
        restored = Feed.restore(
            identifier=original.id,
            **{
                item.name: getattr(original, item.name)
                for item in fields(original)
                if item.name != "id"
            },
        )
        self.assertEqual(restored, original)
        self.assertEqual(
            tuple(item.type_definition for item in restored.schema.fields), variants
        )
        self.assertEqual(
            tuple(item.id for item in restored.schema.fields),
            tuple(item.id for item in definitions),
        )

    def test_type_transforms_are_detached_and_bounded_for_all_variants(self) -> None:
        """Входной список не остаётся mutable-ссылкой, лимит одинаков у трёх типов."""
        for constructor in (ShortTextNodeDataVO, LongTextNodeDataVO, MoneyNodeDataVO):
            is_money = constructor is MoneyNodeDataVO
            arguments = (
                {
                    "currency": UAH,
                    "value_definition": MoneyValueDefinitionVO(MoneyValueMode.MANUAL),
                }
                if is_money
                else {"value_definition": ManualValueDefinitionVO()}
            )
            transform = (
                TransformDefinitionVO(
                    TransformOperation.MONEY_CEIL_STEP,
                    MoneyCeilStepParametersVO(Decimal("1")),
                )
                if is_money
                else TransformDefinitionVO(TransformOperation.STRING_TRIM)
            )
            transforms = [transform]
            definition = constructor(**arguments, transforms=transforms)
            transforms.clear()
            self.assertEqual(definition.transforms, (transform,))
            with self.assertRaises(DefinitionStructureLimitExceededError):
                constructor(**arguments, transforms=[transform] * (MAX_TRANSFORMS + 1))

    def test_money_modes_are_exclusive(self) -> None:
        """Каждый режим имеет единственный допустимый состав и неактивные поля отсутствуют."""
        source = SourceReferenceVO(
            SourceProvider.CATALOG, CatalogSourcePath.REGULAR_PRICE
        )
        calc = PriceCalculationVO(ParameterReferenceVO("price.regular"))
        for mode, src, calculation in (
            (MoneyValueMode.SOURCE, None, None),
            (MoneyValueMode.SOURCE, source, calc),
            (MoneyValueMode.CALCULATED, source, calc),
            (MoneyValueMode.CALCULATED, None, None),
            (MoneyValueMode.MANUAL, source, None),
            ("SOURCE", source, None),
        ):
            with self.subTest(mode=mode), self.assertRaises(InvalidFeedValueError):
                MoneyValueDefinitionVO(mode, src, calculation)

    def test_fallback_chains_are_explicit_canonical_and_detached(self) -> None:
        """Не повторяет локали, не допускает цепочку в NONE и не дублирует целевой язык."""
        locales = [LocaleCodeVO("ru")]
        fallback = LocaleFallbackPolicyVO(LocaleFallbackMode.LOCALE_CHAIN, locales)
        locales.clear()
        self.assertEqual(fallback.locales, (LocaleCodeVO("ru"),))
        self.assertEqual(
            text_field(
                type_definition=ShortTextNodeDataVO(
                    ManualValueDefinitionVO(),
                    locale=LocaleCodeVO("uk"),
                    fallback_policy=fallback,
                )
            ).type_definition.fallback_policy,
            fallback,
        )
        for mode, chain in (
            (LocaleFallbackMode.LOCALE_CHAIN, ()),
            (LocaleFallbackMode.NONE, (LocaleCodeVO("ru"),)),
            (LocaleFallbackMode.LOCALE_CHAIN, (LocaleCodeVO("RU"), LocaleCodeVO("ru"))),
        ):
            with self.assertRaises(InvalidFeedValueError):
                LocaleFallbackPolicyVO(mode, chain)
        with self.assertRaises(InvalidFieldDefinitionError):
            ShortTextNodeDataVO(ManualValueDefinitionVO(), fallback_policy=fallback)
        with self.assertRaises(InvalidFieldDefinitionError):
            ShortTextNodeDataVO(
                ManualValueDefinitionVO(),
                locale=LocaleCodeVO("ru"),
                fallback_policy=fallback,
            )

    def test_export_settings_validate_names_flags_and_single_format(self) -> None:
        """Принимает настройки одного формата и отклоняет коллекции/нетипизированный ввод."""
        self.assertEqual(CsvExportSettingsVO(delimiter="\t").delimiter, "\t")
        for delimiter in ("", "ab", '"', "\n", "\x00"):
            with self.assertRaises(InvalidFeedValueError):
                CsvExportSettingsVO(delimiter=delimiter)
        with self.assertRaises(InvalidFeedValueError):
            CsvExportSettingsVO(include_header=1)
        with self.assertRaises(InvalidFeedValueError):
            XmlExportSettingsVO(root_name="catalog")
        for format_settings in (
            None,
            "csv",
            ExportFormat.CSV,
            {},
            {"format": "csv"},
            (),
            [],
            (CsvExportSettingsVO(),),
            [CsvExportSettingsVO(), XmlExportSettingsVO()],
            FeedProductMode.VARIABLE_TO_SINGLE,
        ):
            with (
                self.subTest(format_settings=format_settings),
                self.assertRaises(InvalidFeedValueError),
            ):
                FeedExportSettingsVO(format_settings=format_settings)
        with self.assertRaisesRegex(TypeError, "format_settings"):
            FeedExportSettingsVO()
        with self.assertRaises(InvalidFeedValueError):
            FeedExportSettingsVO(
                format_settings=CsvExportSettingsVO(), validation_policy="STRICT"
            )
        with self.assertRaises(InvalidFeedValueError):
            FieldExportSettingsVO(ExportNameVO("name"), enabled=1)

    def test_format_settings_have_fixed_formats_and_no_parallel_configuration(
        self,
    ) -> None:
        """Feed хранит настройки одного явно выбранного формата, закреплённого классом VO."""
        settings = FeedExportSettingsVO(format_settings=CsvExportSettingsVO())
        self.assertEqual(settings.format_settings, CsvExportSettingsVO())
        self.assertEqual(
            {item.name for item in fields(settings)},
            {"format_settings", "validation_policy", "product_mode"},
        )
        for constructor, expected_format, other_format in (
            (CsvExportSettingsVO, ExportFormat.CSV, ExportFormat.XML),
            (XmlExportSettingsVO, ExportFormat.XML, ExportFormat.CSV),
        ):
            with self.subTest(constructor=constructor):
                definition = constructor()
                self.assertIs(definition.format, expected_format)
                self.assertNotIn("format", {item.name for item in fields(definition)})
                with self.assertRaisesRegex(TypeError, "format"):
                    constructor(format=other_format)
        for name, definition in (
            ("csv", CsvExportSettingsVO()),
            ("xml", XmlExportSettingsVO()),
            ("formats", (CsvExportSettingsVO(), XmlExportSettingsVO())),
        ):
            self.assertFalse(hasattr(settings, name))
            with self.assertRaisesRegex(TypeError, name):
                FeedExportSettingsVO(
                    format_settings=CsvExportSettingsVO(), **{name: definition}
                )

    def test_selected_format_configuration_survives_create_and_restore(self) -> None:
        """Явный CSV либо XML сохраняет все параметры через обе фабрики без подмены."""
        for format_settings in (
            CsvExportSettingsVO(delimiter=";", include_header=False),
            XmlExportSettingsVO(
                root_name=ExportNameVO("offers"), item_name=ExportNameVO("offer")
            ),
        ):
            with self.subTest(format_settings=format_settings):
                settings = FeedExportSettingsVO(format_settings=format_settings)
                created = feed(export_settings=settings)
                restored = Feed.restore(
                    identifier=created.id,
                    name=created.name,
                    code=created.code,
                    status=created.status,
                    schema=created.schema,
                    export_settings=created.export_settings,
                    created_at=created.created_at,
                    updated_at=created.updated_at,
                )
                self.assertEqual(restored, created)
                for result in (created, restored):
                    self.assertIs(
                        result.export_settings.format_settings, format_settings
                    )
                    self.assertEqual(result.export_settings, settings)
                    self.assertIs(
                        result.export_settings.product_mode,
                        FeedProductMode.VARIABLE_TO_SINGLE,
                    )

    def test_nested_single_format_settings_are_immutable(self) -> None:
        """Не даёт заменить выбранный формат или изменить собственные настройки его VO."""
        csv = CsvExportSettingsVO(delimiter=";")
        xml = XmlExportSettingsVO()
        settings = FeedExportSettingsVO(format_settings=csv)
        for value, attribute, replacement in (
            (settings, "format_settings", xml),
            (csv, "delimiter", ","),
            (xml, "root_name", ExportNameVO("offers")),
        ):
            with (
                self.subTest(attribute=attribute),
                self.assertRaises(FrozenInstanceError),
            ):
                setattr(value, attribute, replacement)

    def test_product_mode_is_single_default_and_settings_are_immutable(self) -> None:
        """Режим по умолчанию имеет стабильный код и не изменяется присваиванием."""
        self.assertEqual(
            FeedProductMode.__members__,
            {"VARIABLE_TO_SINGLE": FeedProductMode.VARIABLE_TO_SINGLE},
        )
        self.assertEqual(FeedProductMode.VARIABLE_TO_SINGLE.value, "VARIABLE_TO_SINGLE")
        settings = FeedExportSettingsVO(format_settings=CsvExportSettingsVO())
        self.assertIs(settings.product_mode, FeedProductMode.VARIABLE_TO_SINGLE)
        self.assertEqual(
            settings,
            FeedExportSettingsVO(
                format_settings=CsvExportSettingsVO(),
                product_mode=FeedProductMode.VARIABLE_TO_SINGLE,
            ),
        )
        with self.assertRaises(FrozenInstanceError):
            settings.product_mode = "VARIABLE_TO_SINGLE"

    def test_product_mode_requires_own_enum_without_implicit_conversion(self) -> None:
        """Отклоняет строки, неизвестные режимы и чужой Enum с тем же кодом."""

        class ForeignProductMode(StrEnum):
            """Имитирует чужой Enum с совпадающим строковым значением."""

            VARIABLE_TO_SINGLE = "VARIABLE_TO_SINGLE"

        for product_mode in (
            "VARIABLE_TO_SINGLE",
            "ONLY_SINGLE",
            "",
            ForeignProductMode.VARIABLE_TO_SINGLE,
            ExportFormat.CSV,
            None,
            False,
            1,
            {},
            [],
        ):
            with (
                self.subTest(product_mode=product_mode),
                self.assertRaises(InvalidFeedValueError),
            ):
                FeedExportSettingsVO(
                    format_settings=CsvExportSettingsVO(), product_mode=product_mode
                )


class FeedCalculationStructureTests(unittest.TestCase):
    """Проверяет определения деревьев и Policy, не исполняя формулы или источники."""

    def test_category_and_presence_rule_can_be_restored_as_a_definition(self) -> None:
        """Набор IF/THEN/ELSE сохраняет порядок, UUID категорий и незавершённые внешние связи."""
        category_id = EntityIdVO(uuid4())
        category = ComparisonConditionVO(
            ComparisonOperator.CONTAINS,
            ParameterReferenceVO("product.category_ids"),
            ScalarLiteralVO(LiteralValueType.UUID, category_id),
        )
        condition = LogicalConditionVO(
            LogicalOperator.ALL,
            [
                category,
                PresenceConditionVO(
                    PresenceOperator.EXISTS, ParameterReferenceVO("price.purchase")
                ),
            ],
        )
        expression = ArithmeticExpressionVO(
            ArithmeticOperator.MULTIPLY,
            left=ParameterReferenceVO("price.purchase"),
            right=DecimalLiteralVO(Decimal("1.25")),
        )
        definition = PriceCalculationVO(
            ParameterReferenceVO("price.regular"),
            [rule(condition, expression)],
            PurchasePriceSourceVO(EntityIdVO(uuid4())),
        )
        result = money_field(definition)
        self.assertEqual(
            result.type_definition.value_definition.calculation.rules[0]
            .condition.operands[0]
            .right.value,
            category_id,
        )
        self.assertFalse(hasattr(definition, "calculate"))
        self.assertFalse(hasattr(expression, "evaluate"))

    def test_rule_and_default_expression_are_required_nodes(self) -> None:
        """Отвергает raw dict/строку и отсутствие ELSE вместо частично корректного объекта."""
        for condition, expression in (
            ({}, ParameterReferenceVO("price.regular")),
            (
                PresenceConditionVO(
                    PresenceOperator.EXISTS, ParameterReferenceVO("price.sale")
                ),
                "price.sale",
            ),
        ):
            with self.assertRaises(InvalidPriceCalculationDefinitionError):
                ConditionalPriceRule.create(
                    identifier=PriceRuleIdVO(uuid4()),
                    condition=condition,
                    expression=expression,
                )
        for expression in (None, {}, "price.regular"):
            with self.assertRaises(InvalidPriceCalculationDefinitionError):
                PriceCalculationVO(expression)
        valid = PriceCalculationVO(ParameterReferenceVO("price.regular"))
        self.assertEqual(
            money_field(valid).type_definition.value_definition.calculation.rules, ()
        )

    def test_rule_entity_is_rechecked_when_attaching_a_calculation(self) -> None:
        """Сырые восстановленные правила не обходят проверку идентификатора/формы."""
        original = rule()
        for invalid in (
            replace(original, id=FieldIdVO(uuid4())),
            replace(original, condition={}),
            replace(original, expression=[]),
        ):
            calculation = PriceCalculationVO(
                ParameterReferenceVO("price.regular"), (invalid,)
            )
            with self.assertRaises(InvalidPriceCalculationDefinitionError):
                money_field(calculation)

    def test_rule_identity_is_scoped_to_a_field_not_the_whole_feed(self) -> None:
        """Два независимых денежных поля могут использовать одинаковый снимок правил."""
        calculation = PriceCalculationVO(
            ParameterReferenceVO("price.regular"), (rule(),)
        )
        first = money_field(calculation)
        second = money_field(
            calculation,
            key=FieldKeyVO("another_amount"),
            export=FieldExportSettingsVO(ExportNameVO("another_amount")),
        )
        self.assertEqual(len(feed(FeedSchemaVO((first, second))).schema.fields), 2)

    def test_currency_tag_does_not_change_source_amount_or_formula(self) -> None:
        """SOURCE и формула не приобретают конвертацию при выборе или смене метки."""
        source = MoneyValueDefinitionVO(
            MoneyValueMode.SOURCE,
            source=SourceReferenceVO(
                SourceProvider.CATALOG, CatalogSourcePath.REGULAR_PRICE
            ),
        )
        original = money_field(
            type_definition=MoneyNodeDataVO(value_definition=source)
        )
        labelled = replace(
            original,
            type_definition=replace(
                original.type_definition, currency=CurrencyVO("usd")
            ),
        )
        self.assertEqual(
            original.type_definition.value_definition,
            labelled.type_definition.value_definition,
        )
        self.assertIsNone(original.type_definition.currency)
        self.assertEqual(labelled.type_definition.currency.value, "USD")
        restored = feed(FeedSchemaVO((labelled,))).schema.fields[0]
        self.assertEqual(restored, labelled)

    def test_price_amount_preserves_zero_negative_and_precise_values(self) -> None:
        """Сумма не округляется и не навязывает ограничения конкретного поля."""
        for value in (Decimal("0"), Decimal("-0.000001"), Decimal("123.123456789")):
            amount = PriceAmountVO(value)
            self.assertEqual(amount.amount.as_tuple(), value.as_tuple())
            with self.assertRaises(FrozenInstanceError):
                amount.amount = Decimal("0")
        with self.assertRaises(TypeError):
            PriceAmountVO(Decimal("1"), currency=UAH)

    def test_formula_preserves_manual_rate_and_markup_without_currency_context(
        self,
    ) -> None:
        """Деление на пользовательский курс и умножение на наценку остаются AST."""
        expression = ArithmeticExpressionVO(
            ArithmeticOperator.MULTIPLY,
            left=ArithmeticExpressionVO(
                ArithmeticOperator.DIVIDE,
                left=ParameterReferenceVO("price.regular"),
                right=DecimalLiteralVO(Decimal("40.123456")),
            ),
            right=DecimalLiteralVO(Decimal("1.20")),
        )
        calculation = PriceCalculationVO(default_expression=expression)
        field = money_field(calculation)
        restored = feed(FeedSchemaVO((field,))).schema.fields[0]
        self.assertEqual(
            restored.type_definition.value_definition.calculation, calculation
        )
        self.assertEqual(
            calculation.default_expression.left.right.value, Decimal("40.123456")
        )
        self.assertEqual(calculation.default_expression.right.value, Decimal("1.20"))

    def test_catalog_purchase_parameter_does_not_require_legacy_binding(self) -> None:
        """Обычный параметр Catalog работает без отдельной закупочной привязки."""
        conditional = rule(
            PresenceConditionVO(
                PresenceOperator.IS_MISSING, ParameterReferenceVO("price.purchase")
            )
        )
        for definition in (
            PriceCalculationVO(ParameterReferenceVO("price.purchase")),
            PriceCalculationVO(ParameterReferenceVO("price.regular"), (conditional,)),
        ):
            field = money_field(definition)
            self.assertEqual(
                field.type_definition.value_definition.calculation, definition
            )
        unused = PriceCalculationVO(
            ParameterReferenceVO("price.regular"),
            purchase_source=PurchasePriceSourceVO(EntityIdVO(uuid4())),
        )
        with self.assertRaises(InvalidPriceCalculationDefinitionError):
            PriceCalculationStructurePolicy.ensure_valid(unused)

    def test_duplicate_rule_ids_are_checked_within_one_calculation(self) -> None:
        """Повтор ID отклоняется, одинаковое содержимое с разными ID допускается."""
        original = rule()
        definition = PriceCalculationVO(
            ParameterReferenceVO("price.regular"), (original, original)
        )
        with self.assertRaises(DuplicatePriceRuleIdentifierError) as caught:
            money_field(definition)
        self.assertEqual(caught.exception.path, ("rules", 1, "id"))
        different_id = rule(original.condition, original.expression)
        valid = PriceCalculationVO(
            ParameterReferenceVO("price.regular"), (original, different_id)
        )
        self.assertEqual(
            money_field(valid).type_definition.value_definition.calculation.rules,
            (original, different_id),
        )

    def test_field_and_feed_restore_recheck_nested_calculation_policy(self) -> None:
        """Вложенный тип не позволяет восстановленной Entity обойти Policy расчёта."""
        original = money_field()
        duplicate = rule()
        calculation = PriceCalculationVO(
            ParameterReferenceVO("price.regular"), (duplicate, duplicate)
        )
        invalid_type = MoneyNodeDataVO(
            currency=UAH,
            value_definition=MoneyValueDefinitionVO(
                MoneyValueMode.CALCULATED, calculation=calculation
            ),
        )
        with self.assertRaises(DuplicatePriceRuleIdentifierError):
            FieldNodeDefinition.restore(
                identifier=original.id,
                key=original.key,
                label=original.label,
                type_definition=invalid_type,
                export=original.export,
            )
        reconstituted = replace(original, type_definition=invalid_type)
        with self.assertRaises(DuplicatePriceRuleIdentifierError):
            Feed.restore(
                identifier=FeedIdVO(uuid4()),
                name=FeedNameVO("Восстановленный"),
                code=FeedCodeVO("restored"),
                status=FeedStatus.DRAFT,
                schema=FeedSchemaVO((reconstituted,)),
                export_settings=FeedExportSettingsVO(
                    format_settings=CsvExportSettingsVO()
                ),
                created_at=NOW,
                updated_at=NOW,
            )

    def test_currency_is_optional_metadata_of_an_unchanged_formula(self) -> None:
        """Код валюты не меняет формулу; расчёт не имеет собственной валюты."""
        calculation = PriceCalculationVO(
            default_expression=ArithmeticExpressionVO(
                operator=ArithmeticOperator.DIVIDE,
                left=ParameterReferenceVO("price.regular"),
                right=DecimalLiteralVO(Decimal("40.123456")),
            ),
        )
        for currency in (None, UAH, CurrencyVO("USD")):
            definition = MoneyNodeDataVO(
                value_definition=MoneyValueDefinitionVO(
                    MoneyValueMode.CALCULATED, calculation=calculation
                ),
                currency=currency,
            )
            result = money_field(type_definition=definition)
            original = feed(FeedSchemaVO((result,)))
            restored = Feed.restore(
                identifier=original.id,
                **{
                    item.name: getattr(original, item.name)
                    for item in fields(original)
                    if item.name != "id"
                },
            )
            self.assertEqual(restored.schema, original.schema)
            settings = restored.schema.fields[0].type_definition
            self.assertEqual(settings.currency, currency)
            self.assertEqual(settings.value_definition.calculation, calculation)
        self.assertEqual(
            {item.name for item in fields(calculation)},
            {"default_expression", "rules", "purchase_source"},
        )
        with self.assertRaises(TypeError):
            PriceCalculationVO(
                default_expression=ParameterReferenceVO("price.regular"),
                calculation_currency=UAH,
            )

    def test_invalid_node_arities_and_literals_are_rejected(self) -> None:
        """Не смешивает бинарную/унарную форму, пустую логику и типы литералов."""
        value = ParameterReferenceVO("price.regular")
        condition = PresenceConditionVO(
            PresenceOperator.EXISTS, ParameterReferenceVO("price.sale")
        )
        for operator, kwargs in (
            (ArithmeticOperator.ADD, {"left": value}),
            (ArithmeticOperator.ADD, {"left": value, "right": value, "operand": value}),
            (ArithmeticOperator.NEGATE, {"left": value, "right": value}),
            (ArithmeticOperator.NEGATE, {"operand": {}}),
        ):
            with self.assertRaises(InvalidFeedValueError):
                ArithmeticExpressionVO(operator, **kwargs)
        self.assertEqual(
            ArithmeticExpressionVO(ArithmeticOperator.NEGATE, operand=value).operand,
            value,
        )
        for operation, args in (
            (PriceFunction.ABS, ()),
            (PriceFunction.ABS, (value, value)),
            (PriceFunction.MIN, (value,)),
        ):
            with self.assertRaises(InvalidFeedValueError):
                FunctionExpressionVO(operation, args)
        for operation, operands in (
            (LogicalOperator.ALL, ()),
            (LogicalOperator.NOT, (condition, condition)),
            (LogicalOperator.ANY, ({},)),
        ):
            with self.assertRaises(InvalidFeedValueError):
                LogicalConditionVO(operation, operands)
        for value_type, raw in (
            (LiteralValueType.UUID, str(uuid4())),
            (LiteralValueType.UUID, uuid4()),
            (LiteralValueType.BOOLEAN, 1),
            (LiteralValueType.STRING, False),
        ):
            with self.assertRaises(InvalidFeedValueError):
                ScalarLiteralVO(value_type, raw)
        self.assertEqual(ScalarLiteralVO(LiteralValueType.BOOLEAN, False).value, False)
        with self.assertRaises(InvalidFeedValueError):
            CollectionLiteralVO(
                LiteralValueType.UUID, (ScalarLiteralVO(LiteralValueType.STRING, "x"),)
            )
        self.assertEqual(CollectionLiteralVO(LiteralValueType.STRING, ()).items, ())

    def test_collection_and_logical_children_are_copied(self) -> None:
        """Коллекции literals и operands не оставляют внешних изменяемых ссылок."""
        item = ScalarLiteralVO(LiteralValueType.UUID, EntityIdVO(uuid4()))
        items = [item]
        collection = CollectionLiteralVO(LiteralValueType.UUID, items)
        conditions = [
            ComparisonConditionVO(
                ComparisonOperator.IN, ParameterReferenceVO("product.id"), collection
            )
        ]
        logic = LogicalConditionVO(LogicalOperator.ALL, conditions)
        items.clear()
        conditions.clear()
        self.assertEqual(collection.items, (item,))
        self.assertEqual(len(logic.operands), 1)

    def test_expression_is_not_executed_or_resolved_early(self) -> None:
        """Деление на ноль и неизвестный реестру параметр остаются только определениями."""
        expression = ArithmeticExpressionVO(
            ArithmeticOperator.DIVIDE,
            left=ParameterReferenceVO("custom.not_registered_yet"),
            right=DecimalLiteralVO(Decimal("0")),
        )
        result = money_field(PriceCalculationVO(expression))
        self.assertIs(
            result.type_definition.value_definition.calculation.default_expression,
            expression,
        )

    def test_depth_limit_is_bounded_and_reports_a_path(self) -> None:
        """Глубокий AST отклоняется итеративно, а не RecursionError."""
        expression = ParameterReferenceVO("price.regular")
        for _ in range(MAX_AST_DEPTH):
            expression = ArithmeticExpressionVO(
                ArithmeticOperator.NEGATE, operand=expression
            )
        with self.assertRaises(DefinitionStructureLimitExceededError) as caught:
            money_field(PriceCalculationVO(expression))
        self.assertEqual(caught.exception.path[0], "default_expression")

    def test_total_node_budget_counts_reused_subtrees(self) -> None:
        """Один shared leaf не позволяет обойти общий бюджет дерева по числу объектов."""
        leaf = ParameterReferenceVO("price.regular")
        expression = FunctionExpressionVO(PriceFunction.MAX, (leaf,) * (MAX_AST_NODES))
        with self.assertRaises(DefinitionStructureLimitExceededError) as caught:
            money_field(PriceCalculationVO(expression))
        self.assertEqual(caught.exception.path[:2], ("default_expression", "arguments"))
        valid = FunctionExpressionVO(PriceFunction.MAX, (leaf,) * (MAX_AST_NODES - 1))
        self.assertIs(
            money_field(
                PriceCalculationVO(valid)
            ).type_definition.value_definition.calculation.default_expression,
            valid,
        )

    def test_limits_for_rule_and_field_collections(self) -> None:
        """Состав ограничивается до обхода или создания лишних объектов."""
        with self.assertRaises(DefinitionStructureLimitExceededError):
            PriceCalculationVO(
                ParameterReferenceVO("price.regular"), (rule(),) * (MAX_RULES + 1)
            )
        with self.assertRaises(DefinitionStructureLimitExceededError):
            FeedSchemaVO((text_field(),) * (MAX_FIELDS + 1))


if __name__ == "__main__":
    unittest.main()
