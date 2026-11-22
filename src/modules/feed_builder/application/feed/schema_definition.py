"""Чистая сборка типизированного определения из закрытого документа Application."""

from decimal import Decimal, InvalidOperation
from typing import cast
from src.modules.feed_builder.application.feed.types import JsonObject, JsonValue
from src.modules.feed_builder.domain.feed.limits import (
    MAX_FIELDS,
    MAX_RULES,
    MAX_AST_DEPTH,
    MAX_AST_NODES,
    MAX_TRANSFORMS,
    MAX_COLLECTION_ITEMS,
)
from src.modules.shared.domain.domain_error import DomainError
from src.modules.shared.domain.value_object.currency import CurrencyVO
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.feed_builder.domain.feed.types import (
    Condition,
    ConditionOperand,
    Expression,
)
from src.modules.feed_builder.application.feed.schema_error import (
    InvalidFeedSchemaDocumentError,
)
from src.modules.feed_builder.domain.feed.entity.field_definition import FieldDefinition
from src.modules.feed_builder.domain.feed.entity.conditional_price_rule import (
    ConditionalPriceRule,
)
from src.modules.feed_builder.domain.feed.enum.arithmetic_operator import (
    ArithmeticOperator,
)
from src.modules.feed_builder.domain.feed.enum.comparison_operator import (
    ComparisonOperator,
)
from src.modules.feed_builder.domain.feed.enum.logical_operator import LogicalOperator
from src.modules.feed_builder.domain.feed.enum.presence_operator import PresenceOperator
from src.modules.feed_builder.domain.feed.enum.literal_value_type import (
    LiteralValueType,
)
from src.modules.feed_builder.domain.feed.enum.price_function import PriceFunction
from src.modules.feed_builder.domain.feed.enum.money_value_mode import MoneyValueMode
from src.modules.feed_builder.domain.feed.enum.source_provider import SourceProvider
from src.modules.feed_builder.domain.feed.enum.catalog_source_path import (
    CatalogSourcePath,
)
from src.modules.feed_builder.domain.feed.enum.transform_operation import (
    TransformOperation,
)
from src.modules.feed_builder.domain.feed.enum.locale_fallback_mode import (
    LocaleFallbackMode,
)
from src.modules.feed_builder.domain.feed.value_object.feed_schema import FeedSchemaVO
from src.modules.feed_builder.domain.feed.value_object.field_id import FieldIdVO
from src.modules.feed_builder.domain.feed.value_object.field_key import FieldKeyVO
from src.modules.feed_builder.domain.feed.value_object.field_label import FieldLabelVO
from src.modules.feed_builder.domain.feed.value_object.field_export_settings import (
    FieldExportSettingsVO,
)
from src.modules.feed_builder.domain.feed.value_object.export_name import ExportNameVO
from src.modules.feed_builder.domain.feed.value_object.string_field_type import (
    StringFieldTypeVO,
)
from src.modules.feed_builder.domain.feed.value_object.text_field_type import (
    TextFieldTypeVO,
)
from src.modules.feed_builder.domain.feed.value_object.money_field_type import (
    MoneyFieldTypeVO,
)
from src.modules.feed_builder.domain.feed.value_object.source_value_definition import (
    SourceValueDefinitionVO,
)
from src.modules.feed_builder.domain.feed.value_object.manual_value_definition import (
    ManualValueDefinitionVO,
)
from src.modules.feed_builder.domain.feed.value_object.money_value_definition import (
    MoneyValueDefinitionVO,
)
from src.modules.feed_builder.domain.feed.value_object.source_reference import (
    SourceReferenceVO,
)
from src.modules.feed_builder.domain.feed.value_object.text_constraints import (
    TextConstraintsVO,
)
from src.modules.feed_builder.domain.feed.value_object.money_constraints import (
    MoneyConstraintsVO,
)
from src.modules.feed_builder.domain.feed.value_object.locale_code import LocaleCodeVO
from src.modules.feed_builder.domain.feed.value_object.locale_fallback_policy import (
    LocaleFallbackPolicyVO,
)
from src.modules.feed_builder.domain.feed.value_object.price_calculation import (
    PriceCalculationVO,
)
from src.modules.feed_builder.domain.feed.value_object.purchase_price_source import (
    PurchasePriceSourceVO,
)
from src.modules.feed_builder.domain.feed.value_object.price_rule_id import (
    PriceRuleIdVO,
)
from src.modules.feed_builder.domain.feed.value_object.parameter_reference import (
    ParameterReferenceVO,
)
from src.modules.feed_builder.domain.feed.value_object.decimal_literal import (
    DecimalLiteralVO,
)
from src.modules.feed_builder.domain.feed.value_object.scalar_literal import (
    ScalarLiteralVO,
)
from src.modules.feed_builder.domain.feed.value_object.collection_literal import (
    CollectionLiteralVO,
)
from src.modules.feed_builder.domain.feed.value_object.arithmetic_expression import (
    ArithmeticExpressionVO,
)
from src.modules.feed_builder.domain.feed.value_object.function_expression import (
    FunctionExpressionVO,
)
from src.modules.feed_builder.domain.feed.value_object.comparison_condition import (
    ComparisonConditionVO,
)
from src.modules.feed_builder.domain.feed.value_object.logical_condition import (
    LogicalConditionVO,
)
from src.modules.feed_builder.domain.feed.value_object.presence_condition import (
    PresenceConditionVO,
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


def document(
    value: object, required: set[str], optional: set[str] | frozenset[str] = frozenset()
) -> JsonObject:
    """Требует объект с известными ключами, не игнорируя неизвестные настройки."""
    if (
        not isinstance(value, dict)
        or not required <= value.keys()
        or value.keys() - required - optional
    ):
        raise InvalidFeedSchemaDocumentError("Некорректные свойства документа.")
    return cast(JsonObject, value)


def string(value: object) -> str:
    """Требует строку без неявного преобразования чисел и null."""
    if not isinstance(value, str):
        raise InvalidFeedSchemaDocumentError("Ожидалась строка в документе.")
    return value


def array(value: object, maximum: int) -> list[JsonValue]:
    """Требует JSON-массив ограниченного размера."""
    if not isinstance(value, list) or len(value) > maximum:
        raise InvalidFeedSchemaDocumentError("Некорректный размер массива документа.")
    return cast(list[JsonValue], value)


def optional_decimal(value: object) -> Decimal | None:
    """Восстанавливает точный Decimal только из ограниченной строки."""
    if value is None:
        return None
    text = string(value)
    if len(text) > 256:
        raise InvalidFeedSchemaDocumentError("Слишком длинная числовая строка.")
    return Decimal(text)


def decode_source(value: object) -> SourceReferenceVO:
    """Восстанавливает закрытую пару provider/path."""
    data = document(value, {"provider", "path"})
    return SourceReferenceVO(
        SourceProvider(string(data["provider"])),
        CatalogSourcePath(string(data["path"])),
    )


class DefinitionReader:
    """Декодирует AST с ограничениями глубины и числа узлов до построения Domain."""

    def __init__(self) -> None:
        """Создаёт отдельный бюджет одного расчёта."""
        self.nodes = 0

    def node(
        self, value: object, depth: int = 1
    ) -> Expression | ConditionOperand | Condition:
        """Восстанавливает конкретный узел без динамического поиска Python-атрибутов."""
        self.nodes += 1
        if depth > MAX_AST_DEPTH or self.nodes > MAX_AST_NODES:
            raise InvalidFeedSchemaDocumentError("Превышен бюджет AST.")
        if not isinstance(value, dict):
            raise InvalidFeedSchemaDocumentError("Узел AST должен быть объектом.")
        kind = value.get("kind")
        if kind == "parameter":
            data = document(value, {"kind", "parameter"})
            return ParameterReferenceVO(string(data["parameter"]))
        if kind == "decimal":
            data = document(value, {"kind", "value"})
            return DecimalLiteralVO(optional_decimal(data["value"]))
        if kind == "scalar":
            data = document(value, {"kind", "value_type", "value"})
            value_type = LiteralValueType(string(data["value_type"]))
            scalar = data["value"]
            if value_type is LiteralValueType.UUID:
                scalar = EntityIdVO.from_value(string(scalar))
            return ScalarLiteralVO(value_type, scalar)
        if kind == "collection":
            data = document(value, {"kind", "item_type", "items"})
            return CollectionLiteralVO(
                LiteralValueType(string(data["item_type"])),
                tuple(
                    self.node(item, depth + 1)
                    for item in array(data["items"], MAX_COLLECTION_ITEMS)
                ),
            )
        if kind == "arithmetic":
            operator = ArithmeticOperator(string(value.get("operator")))
            if operator is ArithmeticOperator.NEGATE:
                data = document(value, {"kind", "operator", "operand"})
                return ArithmeticExpressionVO(
                    operator, operand=self.node(data["operand"], depth + 1)
                )
            data = document(value, {"kind", "operator", "left", "right"})
            return ArithmeticExpressionVO(
                operator,
                left=self.node(data["left"], depth + 1),
                right=self.node(data["right"], depth + 1),
            )
        if kind == "function":
            data = document(value, {"kind", "function", "arguments"})
            return FunctionExpressionVO(
                PriceFunction(string(data["function"])),
                tuple(
                    self.node(item, depth + 1)
                    for item in array(data["arguments"], MAX_AST_NODES)
                ),
            )
        if kind == "comparison":
            data = document(value, {"kind", "operator", "left", "right"})
            return ComparisonConditionVO(
                ComparisonOperator(string(data["operator"])),
                self.node(data["left"], depth + 1),
                self.node(data["right"], depth + 1),
            )
        if kind == "logical":
            data = document(value, {"kind", "operator", "operands"})
            return LogicalConditionVO(
                LogicalOperator(string(data["operator"])),
                tuple(
                    self.node(item, depth + 1)
                    for item in array(data["operands"], MAX_AST_NODES)
                ),
            )
        if kind == "presence":
            data = document(value, {"kind", "operator", "parameter"})
            return PresenceConditionVO(
                PresenceOperator(string(data["operator"])),
                ParameterReferenceVO(string(data["parameter"])),
            )
        raise InvalidFeedSchemaDocumentError("Неизвестный вид узла AST.")

    def calculation(self, value: object) -> PriceCalculationVO:
        """Восстанавливает ELSE, правила и явную привязку закупки."""
        data = document(value, {"default_expression", "rules"}, {"purchase_source"})
        default = self.node(data["default_expression"])
        rules = []
        for item in array(data["rules"], MAX_RULES):
            rule = document(item, {"id", "condition", "expression"})
            rules.append(
                ConditionalPriceRule.restore(
                    identifier=PriceRuleIdVO.from_value(string(rule["id"])),
                    condition=self.node(rule["condition"]),
                    expression=self.node(rule["expression"]),
                )
            )
        purchase_source = None
        if data.get("purchase_source") is not None:
            purchase = document(
                data["purchase_source"], {"provider", "path", "selection"}
            )
            selection = document(purchase["selection"], {"mode", "supplier_source_id"})
            if (
                purchase["provider"] != "supplier_sourcing"
                or purchase["path"] != "purchase_price"
                or selection["mode"] != "SUPPLIER_SOURCE"
            ):
                raise InvalidFeedSchemaDocumentError(
                    "Неизвестная привязка закупочного источника."
                )
            purchase_source = PurchasePriceSourceVO(
                EntityIdVO.from_value(string(selection["supplier_source_id"]))
            )
        return PriceCalculationVO(
            default_expression=default,
            rules=tuple(rules),
            purchase_source=purchase_source,
        )


def decode_transform(value: object) -> TransformDefinitionVO:
    """Восстанавливает конкретный тип параметров преобразования."""
    data = document(value, {"op", "params"})
    operation = TransformOperation(string(data["op"]))
    if operation is TransformOperation.STRING_TRIM:
        document(data["params"], set())
        parameters = None
    elif operation is TransformOperation.STRING_TRUNCATE:
        params = document(data["params"], {"max_length"})
        parameters = TruncateParametersVO(params["max_length"])
    else:
        params = document(data["params"], {"step"})
        parameters = MoneyCeilStepParametersVO(optional_decimal(params["step"]))
    return TransformDefinitionVO(operation, parameters)


def decode_field(value: object) -> FieldDefinition:
    """Восстанавливает поле через явную фабрику и собственные проверки VO."""
    data = document(value, {"id", "key", "label", "type_definition", "export"}, {"ai"})
    raw_type = data["type_definition"]
    if not isinstance(raw_type, dict):
        raise InvalidFeedSchemaDocumentError("Нужен объект настроек типа.")
    kind = raw_type.get("kind")
    transforms = tuple(
        decode_transform(item)
        for item in array(raw_type.get("transforms", []), MAX_TRANSFORMS)
    )
    if kind == "money":
        definition = document(
            raw_type, {"kind", "value"}, {"currency", "constraints", "transforms"}
        )
        constraints = document(
            definition.get("constraints", {}),
            set(),
            {"required", "min_amount", "max_amount"},
        )
        amount = document(
            definition["value"], {"kind", "mode"}, {"source", "calculation"}
        )
        if amount["kind"] != "MONEY":
            raise InvalidFeedSchemaDocumentError("Неверный вид денежного определения.")
        value_definition = MoneyValueDefinitionVO(
            mode=MoneyValueMode(string(amount["mode"])),
            source=decode_source(amount["source"]) if "source" in amount else None,
            calculation=(
                DefinitionReader().calculation(amount["calculation"])
                if "calculation" in amount
                else None
            ),
        )
        field_type = MoneyFieldTypeVO(
            value_definition=value_definition,
            currency=(
                CurrencyVO(string(definition["currency"]))
                if definition.get("currency") is not None
                else None
            ),
            constraints=MoneyConstraintsVO(
                required=constraints.get("required", False),
                min_amount=optional_decimal(constraints.get("min_amount")),
                max_amount=optional_decimal(constraints.get("max_amount")),
            ),
            transforms=transforms,
        )
    elif kind in ("string", "text"):
        definition = document(
            raw_type,
            {"kind", "value"},
            {"locale", "fallback_policy", "constraints", "transforms"},
        )
        constraints = document(
            definition.get("constraints", {}),
            set(),
            {"required", "min_length", "max_length"},
        )
        text_value = document(definition["value"], {"kind"}, {"source"})
        if text_value["kind"] == "SOURCE":
            text_value = document(text_value, {"kind", "source"})
            value_definition = SourceValueDefinitionVO(
                decode_source(text_value["source"])
            )
        elif text_value["kind"] == "MANUAL":
            document(text_value, {"kind"})
            value_definition = ManualValueDefinitionVO()
        else:
            raise InvalidFeedSchemaDocumentError("Неизвестное текстовое определение.")
        fallback = None
        if definition.get("fallback_policy") is not None:
            policy = document(definition["fallback_policy"], {"mode"}, {"locales"})
            fallback = LocaleFallbackPolicyVO(
                LocaleFallbackMode(string(policy["mode"])),
                tuple(
                    LocaleCodeVO(string(item))
                    for item in array(policy.get("locales", []), 32)
                ),
            )
        constructor = StringFieldTypeVO if kind == "string" else TextFieldTypeVO
        field_type = constructor(
            value_definition=value_definition,
            locale=(
                LocaleCodeVO(string(definition["locale"]))
                if definition.get("locale") is not None
                else None
            ),
            fallback_policy=fallback,
            constraints=TextConstraintsVO(
                required=constraints.get("required", False),
                min_length=constraints.get("min_length"),
                max_length=constraints.get("max_length"),
            ),
            transforms=transforms,
        )
    else:
        raise InvalidFeedSchemaDocumentError("Неизвестный тип поля.")
    export = document(data["export"], {"name", "enabled"})
    ai = document(data.get("ai", {"instruction": None}), {"instruction"})
    return FieldDefinition.restore(
        identifier=FieldIdVO.from_value(string(data["id"])),
        key=FieldKeyVO(string(data["key"])),
        label=FieldLabelVO(string(data["label"])),
        type_definition=field_type,
        export=FieldExportSettingsVO(
            ExportNameVO(string(export["name"])), export["enabled"]
        ),
        ai_instruction=ai["instruction"],
    )


def decode_field_at(value: object, index: int) -> FieldDefinition:
    """Дополняет ошибку фабрики адресом поля без потери предметного исключения."""
    try:
        return decode_field(value)
    except DomainError as exc:
        from src.modules.feed_builder.domain.error import FeedBuilderDomainError

        if isinstance(exc, FeedBuilderDomainError):
            exc.path = ("definition", "root", "fields", index) + exc.path
            raise
        raise InvalidFeedSchemaDocumentError(
            str(exc), path=("definition", "root", "fields", index)
        ) from exc
    except (
        InvalidFeedSchemaDocumentError,
        ValueError,
        TypeError,
        KeyError,
        InvalidOperation,
    ) as exc:
        raise InvalidFeedSchemaDocumentError(
            str(exc), path=("definition", "root", "fields", index)
        ) from exc


def decode_schema(value: object) -> FeedSchemaVO:
    """Собирает полную схему с путями ошибок, не обращаясь к хранению."""
    try:
        data = document(value, {"schema_format_version", "root"})
        root = document(data["root"], {"key", "kind", "fields"})
        if root["key"] != "publication" or root["kind"] != "object":
            raise InvalidFeedSchemaDocumentError("Неизвестный корень документа схемы.")
        return FeedSchemaVO(
            tuple(
                decode_field_at(item, index)
                for index, item in enumerate(array(root["fields"], MAX_FIELDS))
            ),
            data["schema_format_version"],
        )
    except InvalidFeedSchemaDocumentError:
        raise
    except DomainError:
        raise
    except (ValueError, TypeError, KeyError, InvalidOperation) as exc:
        raise InvalidFeedSchemaDocumentError("Некорректное определение Feed.") from exc
