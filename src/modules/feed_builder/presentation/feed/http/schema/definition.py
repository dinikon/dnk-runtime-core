from __future__ import annotations
from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator


class ClosedSchema(BaseModel):
    """Запрещает неизвестные свойства и неявное приведение типов HTTP-документа."""

    model_config = ConfigDict(extra="forbid", strict=True)


class SourceSchema(ClosedSchema):
    """Описывает закрытую пару источника, преобразуемую в Domain Enum."""

    provider: Literal["catalog"]
    path: Literal["item.title", "item.description", "item.sku", "item.regular_price"]


class ParameterNode(ClosedSchema):
    """Описывает ссылку на параметр без исполнения выражения."""

    kind: Literal["parameter"]
    parameter: str = Field(max_length=255)


class DecimalNode(ClosedSchema):
    """Сохраняет точную числовую константу строкой."""

    kind: Literal["decimal"]
    value: str = Field(max_length=256)


class ScalarNode(ClosedSchema):
    """Описывает типизированный скаляр условия."""

    kind: Literal["scalar"]
    value_type: Literal["uuid", "string", "boolean"]
    value: str | bool


class CollectionNode(ClosedSchema):
    """Ограничивает коллекцию литералов условия."""

    kind: Literal["collection"]
    item_type: Literal["uuid", "string", "boolean"]
    items: list[ScalarNode] = Field(max_length=500)


class ArithmeticNode(ClosedSchema):
    """Передаёт арифметику; точную арность проверяет сборка Domain."""

    kind: Literal["arithmetic"]
    operator: Literal["ADD", "SUBTRACT", "MULTIPLY", "DIVIDE", "NEGATE"]
    left: Node | None = None
    right: Node | None = None
    operand: Node | None = None


class FunctionNode(ClosedSchema):
    """Описывает разрешённую функцию числового выражения."""

    kind: Literal["function"]
    function: Literal["MIN", "MAX", "ABS"]
    arguments: list[Node] = Field(max_length=4096)


class ComparisonNode(ClosedSchema):
    """Описывает сравнение типизированных операндов."""

    kind: Literal["comparison"]
    operator: Literal["EQ", "NE", "GT", "GTE", "LT", "LTE", "IN", "NOT_IN", "CONTAINS"]
    left: Node
    right: Node


class LogicalNode(ClosedSchema):
    """Описывает ограниченное логическое дерево."""

    kind: Literal["logical"]
    operator: Literal["ALL", "ANY", "NOT"]
    operands: list[Node] = Field(max_length=4096)


class PresenceNode(ClosedSchema):
    """Описывает проверку наличия зарегистрированного параметра."""

    kind: Literal["presence"]
    operator: Literal["EXISTS", "IS_MISSING"]
    parameter: str = Field(max_length=255)


Node = Annotated[
    ParameterNode
    | DecimalNode
    | ScalarNode
    | CollectionNode
    | ArithmeticNode
    | FunctionNode
    | ComparisonNode
    | LogicalNode
    | PresenceNode,
    Field(discriminator="kind"),
]
for node_type in (ArithmeticNode, FunctionNode, ComparisonNode, LogicalNode):
    node_type.model_rebuild()


class PriceRuleSchema(ClosedSchema):
    """Передаёт правило со стабильным идентификатором."""

    id: str = Field(min_length=36, max_length=36)
    condition: Node
    expression: Node


class PurchaseSelectionSchema(ClosedSchema):
    """Описывает явную привязку закупочного источника."""

    mode: Literal["SUPPLIER_SOURCE"]
    supplier_source_id: str = Field(min_length=36, max_length=36)


class PurchaseSourceSchema(ClosedSchema):
    """Сохраняет известную привязку без чтения защищённой суммы."""

    provider: Literal["supplier_sourcing"]
    path: Literal["purchase_price"]
    selection: PurchaseSelectionSchema


class CalculationSchema(ClosedSchema):
    """Позволяет без потерь прочитать и сохранить существующий AST."""

    default_expression: Node
    rules: list[PriceRuleSchema] = Field(max_length=100)
    purchase_source: PurchaseSourceSchema | None = None


class TextSourceValueSchema(ClosedSchema):
    """Передаёт прямой источник текстового поля."""

    kind: Literal["SOURCE"]
    source: SourceSchema


class TextManualValueSchema(ClosedSchema):
    """Задаёт последующее ручное заполнение публикации без значения в схеме."""

    kind: Literal["MANUAL"]


class MoneyValueSchema(ClosedSchema):
    """Передаёт ровно один денежный способ получения значения по правилам Domain."""

    kind: Literal["MONEY"]
    mode: Literal["SOURCE", "MANUAL", "CALCULATED"]
    source: SourceSchema | None = None
    calculation: CalculationSchema | None = None


class TextConstraintsSchema(ClosedSchema):
    """Ограничивает текстовые настройки своим типом."""

    required: bool = False
    min_length: int | None = Field(default=None, ge=0)
    max_length: int | None = Field(default=None, ge=0)


class MoneyConstraintsSchema(ClosedSchema):
    """Сохраняет денежные границы строками без валютной арифметики."""

    required: bool = False
    min_amount: str | None = Field(default=None, max_length=256)
    max_amount: str | None = Field(default=None, max_length=256)


class FallbackSchema(ClosedSchema):
    """Описывает конечную явную цепочку языков."""

    mode: Literal["NONE", "LOCALE_CHAIN", "MANUAL_REQUIRED"]
    locales: list[str] = Field(default_factory=list, max_length=32)


class EmptyParametersSchema(ClosedSchema):
    """Не принимает параметры для операции trim."""


class TruncateParametersSchema(ClosedSchema):
    """Описывает целую длину обрезания."""

    max_length: int = Field(ge=0)


class CeilStepParametersSchema(ClosedSchema):
    """Описывает точный строковый шаг округления."""

    step: str = Field(max_length=256)


class TrimSchema(ClosedSchema):
    """Описывает существующее преобразование trim."""

    op: Literal["string.trim"]
    params: EmptyParametersSchema


class TruncateSchema(ClosedSchema):
    """Описывает существующее преобразование truncate."""

    op: Literal["string.truncate"]
    params: TruncateParametersSchema


class CeilStepSchema(ClosedSchema):
    """Описывает существующее округление суммы вверх."""

    op: Literal["money.ceil_step"]
    params: CeilStepParametersSchema


class TextTypeSchema(ClosedSchema):
    """Ограничивает короткий и длинный текст собственными настройками."""

    kind: Literal["string", "text"]
    value: Annotated[
        TextSourceValueSchema | TextManualValueSchema, Field(discriminator="kind")
    ]
    locale: str | None = Field(default=None, max_length=64)
    fallback_policy: FallbackSchema | None = None
    constraints: TextConstraintsSchema = Field(default_factory=TextConstraintsSchema)
    transforms: list[
        Annotated[TrimSchema | TruncateSchema, Field(discriminator="op")]
    ] = Field(default_factory=list, max_length=128)


class MoneyTypeSchema(ClosedSchema):
    """Хранит сумму с необязательной трёхбуквенной валютной меткой."""

    kind: Literal["money"]
    value: MoneyValueSchema
    currency: str | None = Field(default=None, max_length=16)
    constraints: MoneyConstraintsSchema = Field(default_factory=MoneyConstraintsSchema)
    transforms: list[CeilStepSchema] = Field(default_factory=list, max_length=128)


class FieldExportSchema(ClosedSchema):
    """Передаёт экспортное имя и явное участие поля."""

    name: str = Field(min_length=1, max_length=128)
    enabled: bool


class FieldAiSchema(ClosedSchema):
    """Сохраняет существующие метаданные без запуска AI."""

    instruction: str | None = Field(default=None, max_length=10000)


class DefinitionFieldSchema(ClosedSchema):
    """Объединяет общие свойства Entity с закрытым описанием типа."""

    id: str = Field(min_length=36, max_length=36)
    key: str = Field(min_length=1, max_length=128)
    label: str = Field(min_length=1, max_length=255)
    type_definition: Annotated[
        TextTypeSchema | MoneyTypeSchema, Field(discriminator="kind")
    ]
    export: FieldExportSchema
    ai: FieldAiSchema = Field(default_factory=FieldAiSchema)


class SchemaRoot(ClosedSchema):
    """Хранит упорядоченный плоский состав, включая пустой."""

    key: Literal["publication"]
    kind: Literal["object"]
    fields: list[DefinitionFieldSchema] = Field(max_length=200)


class SchemaDefinition(ClosedSchema):
    """Передаёт единственную поддержанную форму рабочей схемы."""

    schema_format_version: Literal[1]
    root: SchemaRoot

    @field_validator("schema_format_version", mode="before")
    @classmethod
    def require_version_integer(cls, value: object) -> int:
        """Не принимает boolean вместо числовой версии документа."""
        if type(value) is not int or value != 1:
            raise ValueError("Поддерживается целая версия документа 1.")
        return value
