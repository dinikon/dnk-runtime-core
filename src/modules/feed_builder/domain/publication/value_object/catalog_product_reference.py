from dataclasses import dataclass
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.feed_builder.domain.publication.error import (
    InvalidPublicationValueError,
)


@dataclass(frozen=True, slots=True)
class CatalogProductReferenceVO:
    """Ссылается на простой товар либо конкретный вариант указанного родителя."""

    catalog_item_id: EntityIdVO
    catalog_variant_id: EntityIdVO | None = None

    def __post_init__(self) -> None:
        """Проверяет форму ссылки; существование и принадлежность проверяются снаружи."""
        if (
            not isinstance(self.catalog_item_id, EntityIdVO)
            or (
                self.catalog_variant_id is not None
                and not isinstance(self.catalog_variant_id, EntityIdVO)
            )
            or (
                self.catalog_variant_id is not None
                and self.catalog_variant_id.uuid == self.catalog_item_id.uuid
            )
        ):
            raise InvalidPublicationValueError(
                "Некорректная ссылка на позицию Catalog."
            )
