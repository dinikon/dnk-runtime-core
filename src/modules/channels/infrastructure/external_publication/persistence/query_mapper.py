from decimal import Decimal
from typing import Any, Mapping, Sequence
from src.modules.channels.application.external_publication.query.list_publications.dto import (
    PublicationListItemDTO,
)
from src.modules.channels.application.external_publication.query.get_publication.dto import (
    PublicationDetailsDTO,
    PublicationVariantDTO,
    PublicationImageDTO,
    PublicationCategoryDTO,
    PublicationAttributeDTO,
)


def decimal_value(value: str | None) -> Decimal | None:
    """Восстанавливает nullable денежное значение SQL-проекции."""
    return None if value is None else Decimal(value)


class PublicationQueryMapper:
    """Создаёт DTO списка и карточки без восстановления доменного агрегата."""

    @staticmethod
    def to_list_item(row: Mapping[str, Any]) -> PublicationListItemDTO:
        """Собирает строку из минимальной проекции без описания и native JSON."""
        values = dict(row)
        values["price"] = decimal_value(values["price"])
        return PublicationListItemDTO(**values)

    @staticmethod
    def to_variant(row: Mapping[str, Any]) -> PublicationVariantDTO:
        """Собирает поля вариации в контракт детализации публикации."""
        doc = row["document"]
        return PublicationVariantDTO(
            id=row["id"],
            external_id=row["external_id"],
            title=doc["title"],
            sku=doc["sku"],
            price=decimal_value(doc["price"]),
            currency=doc["currency"],
            quantity=decimal_value(doc["quantity"]),
            availability=doc["availability"],
            source_status=doc["source_status"],
            attributes=tuple(
                PublicationAttributeDTO(**value) for value in doc["attributes"]
            ),
        )

    @staticmethod
    def to_details(
        row: Mapping[str, Any], children: Sequence[Mapping[str, Any]]
    ) -> PublicationDetailsDTO:
        """Собирает карточку из нормализованного документа и связанных позиций."""
        values = dict(row["document"])
        for key in ("price", "regular_price", "sale_price", "quantity"):
            values[key] = decimal_value(values[key])
        values["images"] = tuple(
            PublicationImageDTO(**value) for value in values["images"]
        )
        values["categories"] = tuple(
            PublicationCategoryDTO(**value) for value in values["categories"]
        )
        values["attributes"] = tuple(
            PublicationAttributeDTO(**value) for value in values["attributes"]
        )
        values["warnings"] = tuple(values["warnings"])
        return PublicationDetailsDTO(
            id=row["id"],
            channel_id=row["channel_id"],
            external_id=row["external_id"],
            resource_type=row["resource_type"],
            revision=row["revision"],
            observed_at=row["observed_at"],
            variants=tuple(
                PublicationQueryMapper.to_variant(child) for child in children
            ),
            **values,
        )
