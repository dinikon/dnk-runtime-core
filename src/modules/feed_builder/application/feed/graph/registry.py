from collections.abc import Callable
from dataclasses import dataclass

from src.modules.feed_builder.application.feed.graph.category_codec import (
    category_field_document,
    decode_category_field,
)
from src.modules.feed_builder.application.feed.graph.money_codec import (
    read_money,
    write_money,
)
from src.modules.feed_builder.application.feed.graph.numeric_bool_codec import (
    read_numeric_bool,
    write_numeric_bool,
)
from src.modules.feed_builder.application.feed.graph.text_codec import (
    read_text,
    write_text,
)
from src.modules.feed_builder.application.feed.graph.error import (
    InvalidFeedSchemaDocumentError,
)
from src.modules.feed_builder.application.feed.types import JsonObject
from src.modules.feed_builder.domain.feed.enum.field_value_type import FieldValueType
from src.modules.feed_builder.domain.feed.field_node.boolean.value_object.data import (
    BooleanNodeDataVO,
)
from src.modules.feed_builder.domain.feed.field_node.category.value_object.data import (
    CategoryNodeDataVO,
)
from src.modules.feed_builder.domain.feed.field_node.integer.value_object.data import (
    IntegerNodeDataVO,
)
from src.modules.feed_builder.domain.feed.field_node.long_text.value_object.data import (
    LongTextNodeDataVO,
)
from src.modules.feed_builder.domain.feed.field_node.rich_text.value_object.data import (
    RichTextNodeDataVO,
)
from src.modules.feed_builder.domain.feed.field_node.money.value_object.data import (
    MoneyNodeDataVO,
)
from src.modules.feed_builder.domain.feed.field_node.short_text.value_object.data import (
    ShortTextNodeDataVO,
)
from src.modules.feed_builder.domain.feed.types import FieldTypeDefinition


@dataclass(frozen=True, slots=True)
class NodeCodec:
    """Связывает тип и версию ноды с конкретным представлением её данных."""

    kind: FieldValueType
    type_id: str
    label: str
    modes: tuple[str, ...]
    read: Callable[[JsonObject, CategoryNodeDataVO | None], FieldTypeDefinition]
    write: Callable[[FieldTypeDefinition], JsonObject]
    version: int = 1


def register[DataT: FieldTypeDefinition](
    kind: FieldValueType,
    type_id: str,
    label: str,
    modes: tuple[str, ...],
    data_type: type[DataT],
    read_data: Callable[[JsonObject], FieldTypeDefinition],
    write_data: Callable[[DataT], JsonObject],
) -> NodeCodec:
    """Проверяет вход и результат конкретного кодека на общей границе графа."""

    def read(
        document: JsonObject, previous: CategoryNodeDataVO | None
    ) -> FieldTypeDefinition:
        """Декодирует конфигурацию зарегистрированного типа."""
        value = read_data(document)
        if not isinstance(value, data_type):
            raise InvalidFeedSchemaDocumentError("Некорректные данные типа ноды.")
        return value

    def write(value: FieldTypeDefinition) -> JsonObject:
        """Сериализует только конфигурацию соответствующего типа."""
        if not isinstance(value, data_type):
            raise InvalidFeedSchemaDocumentError("Некорректные данные типа ноды.")
        return write_data(value)

    return NodeCodec(kind, type_id, label, modes, read, write)


_MODES = ("SOURCE", "MANUAL", "CONSTANT")
NODE_CODECS = (
    register(
        FieldValueType.STRING,
        "core.short_text",
        "Короткий текст",
        _MODES,
        ShortTextNodeDataVO,
        read_text,
        write_text,
    ),
    register(
        FieldValueType.TEXT,
        "core.long_text",
        "Длинный текст",
        _MODES,
        LongTextNodeDataVO,
        read_text,
        write_text,
    ),
    register(
        FieldValueType.RICH_TEXT,
        "core.rich_text",
        "Длинный текст (HTML)",
        _MODES,
        RichTextNodeDataVO,
        read_text,
        write_text,
    ),
    register(
        FieldValueType.MONEY,
        "core.money",
        "Денежное значение",
        ("SOURCE", "MANUAL", "CALCULATED"),
        MoneyNodeDataVO,
        read_money,
        write_money,
    ),
    register(
        FieldValueType.INTEGER,
        "core.integer",
        "Целое число",
        _MODES,
        IntegerNodeDataVO,
        read_numeric_bool,
        write_numeric_bool,
    ),
    register(
        FieldValueType.BOOLEAN,
        "core.boolean",
        "Логическое значение",
        (*_MODES, "CALCULATED"),
        BooleanNodeDataVO,
        read_numeric_bool,
        write_numeric_bool,
    ),
    NodeCodec(
        FieldValueType.CATEGORY,
        "core.category_reference",
        "Категория",
        ("INLINE",),
        decode_category_field,
        category_field_document,
    ),
)
_BY_KIND = {item.kind.value: item for item in NODE_CODECS}
_BY_ID = {(item.type_id, item.version): item for item in NODE_CODECS}


def node_codec(kind: object) -> NodeCodec:
    """Находит кодек по доменному типу ноды."""
    codec = _BY_KIND.get(kind) if isinstance(kind, str) else None
    if codec is None:
        raise InvalidFeedSchemaDocumentError("Неизвестный тип поля.")
    return codec


def versioned_node_codec(type_id: str, version: int) -> NodeCodec:
    """Находит точную зарегистрированную версию типа."""
    codec = _BY_ID.get((type_id, version))
    if codec is None:
        raise InvalidFeedSchemaDocumentError("Тип или версия ноды недоступны.")
    return codec
