"""Типизированные объединения определений; классы VO находятся в отдельных файлах."""

from src.modules.feed_builder.domain.feed.field_node.category.value_object.data import (
    CategoryNodeDataVO,
)
from src.modules.feed_builder.domain.feed.value_object.price_value import PriceValueVO
from src.modules.feed_builder.domain.feed.expression.value_object.parameter_reference import (
    ParameterReferenceVO,
)
from src.modules.feed_builder.domain.feed.expression.value_object.decimal_literal import (
    DecimalLiteralVO,
)
from src.modules.feed_builder.domain.feed.expression.value_object.arithmetic_expression import (
    ArithmeticExpressionVO,
)
from src.modules.feed_builder.domain.feed.expression.value_object.function_expression import (
    FunctionExpressionVO,
)
from src.modules.feed_builder.domain.feed.expression.value_object.scalar_literal import (
    ScalarLiteralVO,
)
from src.modules.feed_builder.domain.feed.expression.value_object.collection_literal import (
    CollectionLiteralVO,
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
from src.modules.feed_builder.domain.feed.value_object.source_value_definition import (
    SourceValueDefinitionVO,
)
from src.modules.feed_builder.domain.feed.value_object.manual_value_definition import (
    ManualValueDefinitionVO,
)
from src.modules.feed_builder.domain.feed.value_object.text_constant_value_definition import (
    TextConstantValueDefinitionVO,
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
from src.modules.feed_builder.domain.feed.value_object.csv_export_settings import (
    CsvExportSettingsVO,
)
from src.modules.feed_builder.domain.feed.value_object.xml_export_settings import (
    XmlExportSettingsVO,
)

from src.modules.feed_builder.domain.feed.field_node.boolean.value_object.data import (
    BooleanNodeDataVO,
)
from src.modules.feed_builder.domain.feed.field_node.integer.value_object.data import (
    IntegerNodeDataVO,
)

type Expression = ParameterReferenceVO | DecimalLiteralVO | ArithmeticExpressionVO | FunctionExpressionVO
type ConditionOperand = Expression | ScalarLiteralVO | CollectionLiteralVO
type Condition = ComparisonConditionVO | LogicalConditionVO | PresenceConditionVO
type TextValueDefinition = SourceValueDefinitionVO | ManualValueDefinitionVO | TextConstantValueDefinitionVO
type TextFieldType = ShortTextNodeDataVO | LongTextNodeDataVO
type ScalarFieldType = IntegerNodeDataVO | BooleanNodeDataVO
type FieldTypeDefinition = TextFieldType | MoneyNodeDataVO | ScalarFieldType | CategoryNodeDataVO
type ResolvedFieldValue = str | int | bool | PriceValueVO | None
type ExportFormatSettings = CsvExportSettingsVO | XmlExportSettingsVO
