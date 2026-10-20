from collections.abc import Mapping, Sequence
from typing import Any
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.channels.domain.product_representation.aggregate import (
    ProductRepresentation,
)
from src.modules.channels.domain.product_representation.entity.external_binding import (
    ExternalBinding,
)


class ProductRepresentationMapper:
    """Чисто восстанавливает корень и внутренние Entities через фабрики Domain."""

    @staticmethod
    def to_domain(
        row: Mapping[str, Any], bindings: Sequence[Mapping[str, Any]]
    ) -> ProductRepresentation:
        """Оставляет проверку инвариантов восстановления в Domain."""
        return ProductRepresentation.restore(
            EntityIdVO(row["id"]),
            EntityIdVO(row["connection_id"]),
            EntityIdVO(row["catalog_item_id"]),
            row["revision"],
            [
                ExternalBinding.restore(
                    EntityIdVO(b["id"]),
                    EntityIdVO(b["publication_id"]),
                    b["created_at"],
                    EntityIdVO(b["created_by"]),
                    b["released_at"],
                    EntityIdVO(b["released_by"]) if b["released_by"] else None,
                )
                for b in bindings
            ],
        )

    @staticmethod
    def to_values(item: ProductRepresentation) -> dict[str, Any]:
        """Готовит строку хранения, не выполняя I/O."""
        return dict(
            id=item.id.uuid,
            connection_id=item.connection_id.uuid,
            catalog_item_id=item.catalog_item_id.uuid,
            revision=item.revision,
        )

    @staticmethod
    def binding_values(
        item: ProductRepresentation, binding: ExternalBinding
    ) -> dict[str, Any]:
        """Готовит строку внутренней связи."""
        return dict(
            id=binding.id.uuid,
            representation_id=item.id.uuid,
            publication_id=binding.publication_id.uuid,
            created_at=binding.created_at,
            created_by=binding.created_by.uuid,
            released_at=binding.released_at,
            released_by=binding.released_by.uuid if binding.released_by else None,
        )
