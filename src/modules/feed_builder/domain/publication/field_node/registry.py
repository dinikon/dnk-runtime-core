from typing import Protocol

from src.modules.feed_builder.domain.feed.entity.field_node import FieldNodeDefinition
from src.modules.feed_builder.domain.feed.error import InvalidFieldDefinitionError
from src.modules.feed_builder.domain.publication.field_node.money.node import MoneyNode
from src.modules.feed_builder.domain.publication.field_node.result import ResolvedField
from src.modules.feed_builder.domain.publication.field_node.scalar.node import (
    ScalarNode,
)
from src.modules.feed_builder.domain.publication.field_node.text.node import TextNode
from src.modules.feed_builder.domain.publication.value_object.field_override import (
    FieldOverrideVO,
)
from src.modules.feed_builder.domain.publication.value_object.publication_catalog_snapshot import (
    PublicationCatalogSnapshotVO,
)


class RegisteredFieldNode(Protocol):
    """Предоставляет исполнение сквозному сценарию без знания конфигурации ноды."""

    @property
    def data_type(self) -> type | tuple[type, ...]:
        """Возвращает Python-типы конфигурации зарегистрированной реализации."""
        ...

    def resolve(
        self, field: FieldNodeDefinition, snapshot: PublicationCatalogSnapshotVO
    ) -> ResolvedField:
        """Вычисляет автоматическое значение."""
        ...

    def resolve_override(
        self,
        field: FieldNodeDefinition,
        snapshot: PublicationCatalogSnapshotVO,
        override: FieldOverrideVO,
    ) -> ResolvedField:
        """Нормализует явную перезапись."""
        ...

    def check_override(
        self, field: FieldNodeDefinition, override: FieldOverrideVO
    ) -> ResolvedField | None:
        """Возвращает ошибку ручного ввода, если значение выходит за ограничения."""
        ...


class FieldNodeRegistry:
    """Находит единственную реализацию для типизированной конфигурации поля."""

    def __init__(self, nodes: tuple[RegisteredFieldNode, ...]) -> None:
        """Регистрирует реализации по типам данных при сборке вычислителя."""
        self._nodes: dict[type, RegisteredFieldNode] = {}
        for node in nodes:
            settings = node.data_type
            for data_type in settings if isinstance(settings, tuple) else (settings,):
                if data_type in self._nodes:
                    raise InvalidFieldDefinitionError(
                        "Тип данных ноды зарегистрирован дважды."
                    )
                self._nodes[data_type] = node

    def for_field(self, field: FieldNodeDefinition) -> RegisteredFieldNode:
        """Возвращает реализацию по фактическому типу данных сохранённой ноды."""
        node = self._nodes.get(type(field.type_definition))
        if node is None:
            raise InvalidFieldDefinitionError("Нет реализации типа ноды.")
        return node


PUBLICATION_NODES = FieldNodeRegistry((TextNode(), ScalarNode(), MoneyNode()))
