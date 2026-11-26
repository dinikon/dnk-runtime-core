from src.modules.feed_builder.domain.feed.entity.field_node import FieldNodeDefinition
from src.modules.feed_builder.domain.feed.expression.value_object.calculation_inputs import (
    CalculationInputsVO,
)
from src.modules.feed_builder.domain.publication.field_node.registry import (
    FieldNodeRegistry,
    PUBLICATION_NODES,
)
from src.modules.feed_builder.domain.publication.field_node.result import ResolvedField
from src.modules.feed_builder.domain.publication.value_object.field_override import (
    FieldOverrideVO,
)
from src.modules.feed_builder.domain.publication.value_object.publication_catalog_snapshot import (
    PublicationCatalogSnapshotVO,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


class NodeValueResolver:
    """Выбирает ручное или автоматическое значение на уровне публикации."""

    def __init__(self, registry: FieldNodeRegistry = PUBLICATION_NODES) -> None:
        """Получает зарегистрированные реализации типов."""
        self._registry = registry

    def resolve_manual(
        self,
        field: FieldNodeDefinition,
        override: FieldOverrideVO,
        product_id: EntityIdVO,
    ) -> ResolvedField:
        """Валидирует ручное значение без загрузки исходного товара."""
        node = self._registry.for_field(field)
        invalid = node.check_override(field, override)
        if invalid is not None:
            return invalid
        return node.resolve_override(
            field,
            PublicationCatalogSnapshotVO(
                CalculationInputsVO(product_id, None, None, None, None), ()
            ),
            override,
        )

    def resolve(
        self,
        field: FieldNodeDefinition,
        snapshot: PublicationCatalogSnapshotVO,
        override: FieldOverrideVO | None,
    ) -> ResolvedField:
        """Передаёт явную перезапись в ноду либо вызывает автоматический расчёт."""
        node = self._registry.for_field(field)
        if override is not None:
            return node.resolve_override(field, snapshot, override)
        return node.resolve(field, snapshot)
