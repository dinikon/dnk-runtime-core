"""Типизированные объединения определений; классы VO находятся в отдельных файлах."""

from src.modules.feed_builder.domain.feed.value_object.parameter_reference import (
    ParameterReferenceVO,
)
from src.modules.feed_builder.domain.feed.value_object.decimal_literal import (
    DecimalLiteralVO,
)
from src.modules.feed_builder.domain.feed.value_object.money_literal import (
    MoneyLiteralVO,
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

type Expression = ParameterReferenceVO | DecimalLiteralVO | MoneyLiteralVO | ArithmeticExpressionVO | FunctionExpressionVO
type ConditionOperand = Expression | ScalarLiteralVO | CollectionLiteralVO
type Condition = ComparisonConditionVO | LogicalConditionVO | PresenceConditionVO
type TextValueDefinition = SourceValueDefinitionVO | ManualValueDefinitionVO
type FieldTypeDefinition = StringFieldTypeVO | TextFieldTypeVO | MoneyFieldTypeVO
type ExportFormatSettings = CsvExportSettingsVO | XmlExportSettingsVO
