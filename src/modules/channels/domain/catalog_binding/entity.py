from dataclasses import dataclass
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.channels.domain.catalog_binding.error import CatalogBindingError


@dataclass(frozen=True, slots=True)
class CatalogBindingItem:
    """Принадлежащая группе явная пара продаваемых позиций."""

    id: EntityIdVO
    catalog_position_id: EntityIdVO
    publication_id: EntityIdVO

    @classmethod
    def create(
        cls,
        *,
        identifier: EntityIdVO,
        catalog_position_id: EntityIdVO,
        publication_id: EntityIdVO,
    ) -> "CatalogBindingItem":
        """Создаёт пару с проверкой идентичностей."""
        return cls.restore(
            identifier=identifier,
            catalog_position_id=catalog_position_id,
            publication_id=publication_id,
        )

    @classmethod
    def restore(
        cls,
        *,
        identifier: EntityIdVO,
        catalog_position_id: EntityIdVO,
        publication_id: EntityIdVO,
    ) -> "CatalogBindingItem":
        """Отклоняет повреждённое представление пары."""
        if (
            not isinstance(identifier, EntityIdVO)
            or not isinstance(catalog_position_id, EntityIdVO)
            or not isinstance(publication_id, EntityIdVO)
        ):
            raise CatalogBindingError("binding_item_invalid")
        return cls(identifier, catalog_position_id, publication_id)
