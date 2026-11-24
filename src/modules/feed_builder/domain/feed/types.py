"""Типизированные объединения определений; классы VO находятся в отдельных файлах."""

from src.modules.feed_builder.domain.feed.value_object.category_field_type import (
    CategoryFieldTypeVO,
)
from src.modules.feed_builder.domain.feed.value_object.price_value import PriceValueVO
from src.modules.feed_builder.domain.feed.value_object.parameter_reference import (
    ParameterReferenceVO,
)
from src.modules.feed_builder.domain.feed.value_object.decimal_literal import (
    DecimalLiteralVO,
)
from src.modules.feed_builder.domain.feed.value_object.arithmetic_expression import (
    ArithmeticExpressionVO,
)
from src.modules.feed_builder.domain.feed.value_object.function_expression import (
    FunctionExpressionVO,
)
from src.modules.feed_builder.domain.feed.value_object.scalar_literal import (
    ScalarLiteralVO,
)
from src.modules.feed_builder.domain.feed.value_object.collection_literal import (
    CollectionLiteralVO,
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
from src.modules.feed_builder.domain.feed.value_object.source_value_definition import (
    SourceValueDefinitionVO,
)
from src.modules.feed_builder.domain.feed.value_object.manual_value_definition import (
    ManualValueDefinitionVO,
)
from src.modules.feed_builder.domain.feed.value_object.text_constant_value_definition import (
    TextConstantValueDefinitionVO,
)
from src.modules.feed_builder.domain.feed.value_object.string_field_type import (
    StringFieldTypeVO,
)
from src.modules.feed_builder.domain.feed.value_object.text_field_type import (
    TextFieldTypeVO,
)
from src.modules.feed_builder.domain.feed.value_object.money_field_type import (
    MoneyFieldTypeVO,
)
from src.modules.feed_builder.domain.feed.value_object.csv_export_settings import (
    CsvExportSettingsVO,
)
from src.modules.feed_builder.domain.feed.value_object.xml_export_settings import (
    XmlExportSettingsVO,
)

from src.modules.feed_builder.domain.feed.value_object.boolean_field_type import (
    BooleanFieldTypeVO,
)
from src.modules.feed_builder.domain.feed.value_object.integer_field_type import (
    IntegerFieldTypeVO,
)

type Expression = ParameterReferenceVO | DecimalLiteralVO | ArithmeticExpressionVO | FunctionExpressionVO
type ConditionOperand = Expression | ScalarLiteralVO | CollectionLiteralVO
type Condition = ComparisonConditionVO | LogicalConditionVO | PresenceConditionVO
type TextValueDefinition = SourceValueDefinitionVO | ManualValueDefinitionVO | TextConstantValueDefinitionVO
type TextFieldType = StringFieldTypeVO | TextFieldTypeVO
type ScalarFieldType = IntegerFieldTypeVO | BooleanFieldTypeVO
type FieldTypeDefinition = TextFieldType | MoneyFieldTypeVO | ScalarFieldType | CategoryFieldTypeVO
type ResolvedFieldValue = str | int | bool | PriceValueVO | None
type ExportFormatSettings = CsvExportSettingsVO | XmlExportSettingsVO
