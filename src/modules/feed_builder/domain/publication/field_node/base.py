from abc import ABC, abstractmethod

from src.modules.feed_builder.domain.feed.entity.field_node import FieldNodeDefinition
from src.modules.feed_builder.domain.feed.error import InvalidFieldDefinitionError
from src.modules.feed_builder.domain.publication.field_node.result import (
    FieldIssue,
    ResolvedField,
)
from src.modules.feed_builder.domain.publication.value_object.field_override import (
    FieldOverrideVO,
)
from src.modules.feed_builder.domain.publication.value_object.publication_catalog_snapshot import (
    PublicationCatalogSnapshotVO,
)


class FieldNode[DataT](ABC):
    """Вычисляет зарегистрированный тип поля из типизированных настроек и снимка."""

    data_type: type[DataT] | tuple[type[DataT], ...]

    def data(self, field: FieldNodeDefinition) -> DataT:
        """Проверяет соответствие конфигурации зарегистрированной реализации."""
        value = field.type_definition
        if not isinstance(value, self.data_type):
            raise InvalidFieldDefinitionError("Настройки не соответствуют типу ноды.")
        return value

    def resolve(
        self, field: FieldNodeDefinition, snapshot: PublicationCatalogSnapshotVO
    ) -> ResolvedField:
        """Вычисляет автоматическое значение."""
        return self.resolve_value(field, self.data(field), snapshot, None)

    def resolve_override(
        self,
        field: FieldNodeDefinition,
        snapshot: PublicationCatalogSnapshotVO,
        override: FieldOverrideVO,
    ) -> ResolvedField:
        """Проверяет и нормализует переданное ручное значение."""
        return self.resolve_value(field, self.data(field), snapshot, override)

    def check_override(
        self, field: FieldNodeDefinition, override: FieldOverrideVO
    ) -> ResolvedField | None:
        """Проверяет ограничения ввода до применения преобразований."""
        return None

    @abstractmethod
    def resolve_value(
        self,
        field: FieldNodeDefinition,
        settings: DataT,
        snapshot: PublicationCatalogSnapshotVO,
        override: FieldOverrideVO | None,
    ) -> ResolvedField:
        """Разрешает значение с общими правилами конкретного типа."""
        ...


def invalid_value(
    field: FieldNodeDefinition, origin: str, code: str, message: str
) -> ResolvedField:
    """Возвращает ошибку одного поля без частичного значения."""
    return ResolvedField(
        field.id.uuid,
        None,
        origin,
        issues=(FieldIssue(field.id.uuid, code, message),),
    )
