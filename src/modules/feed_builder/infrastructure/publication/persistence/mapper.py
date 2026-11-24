from collections.abc import Mapping
from datetime import datetime
from decimal import Decimal
from uuid import UUID
from typing import cast
from src.modules.feed_builder.domain.publication.aggregate import FeedPublication
from src.modules.feed_builder.domain.publication.enum.publication_status import (
    PublicationStatus,
)
from src.modules.feed_builder.domain.publication.value_object.feed_publication_id import (
    FeedPublicationIdVO,
)
from src.modules.feed_builder.domain.publication.value_object.feed_publication_version import (
    FeedPublicationVersionVO,
)
from src.modules.feed_builder.domain.publication.value_object.catalog_product_reference import (
    CatalogProductReferenceVO,
)
from src.modules.feed_builder.domain.publication.value_object.field_override import (
    FieldOverrideVO,
)
from src.modules.feed_builder.domain.feed.value_object.field_id import FieldIdVO
from src.modules.feed_builder.domain.feed.value_object.price_amount import PriceAmountVO
from src.modules.feed_builder.domain.feed.value_object.feed_id import FeedIdVO
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


class InvalidPublicationStorageError(Exception):
    """Не маскирует повреждённые ручные значения как пустой набор."""


class FeedPublicationMapper:
    """Восстанавливает агрегат и точно сериализует все ручные значения без I/O."""

    @staticmethod
    def read_overrides(overrides: object) -> tuple[FieldOverrideVO, ...]:
        """Читает JSON ручных значений без восстановления агрегата."""
        if not isinstance(overrides, dict):
            raise InvalidPublicationStorageError("Неверные overrides.")
        values: list[FieldOverrideVO] = []
        for identifier, entry in overrides.items():
            if (
                not isinstance(entry, dict)
                or set(entry) != {"mode", "value"}
                or entry["mode"] != "MANUAL"
            ):
                raise InvalidPublicationStorageError("Неверное ручное значение.")
            value = entry["value"]
            if isinstance(value, dict):
                if set(value) != {"amount"} or not isinstance(value["amount"], str):
                    raise InvalidPublicationStorageError("Неверная денежная сумма.")
                value = PriceAmountVO(Decimal(value["amount"]))
            if value is not None and not isinstance(
                value, (str, int, bool, PriceAmountVO)
            ):
                raise InvalidPublicationStorageError("Неверный тип ручного значения.")
            values.append(FieldOverrideVO(FieldIdVO(UUID(identifier)), value))
        return tuple(values)

    @staticmethod
    def to_domain(row: Mapping[str, object]) -> FeedPublication:
        """Использует restore с именованными аргументами и реальной версией."""
        return FeedPublication.restore(
            identifier=FeedPublicationIdVO(cast(UUID, row["id"])),
            feed_id=FeedIdVO(cast(UUID, row["feed_id"])),
            product_reference=CatalogProductReferenceVO(
                EntityIdVO(cast(UUID, row["catalog_item_id"])),
                (
                    EntityIdVO(cast(UUID, row["catalog_variant_id"]))
                    if row["catalog_variant_id"] is not None
                    else None
                ),
            ),
            status=PublicationStatus(cast(str, row["status"])),
            overrides=FeedPublicationMapper.read_overrides(row["overrides"]),
            created_at=cast(datetime, row["created_at"]),
            updated_at=cast(datetime, row["updated_at"]),
            version=FeedPublicationVersionVO(cast(int, row["row_version"])),
        )

    @staticmethod
    def write_overrides(overrides: tuple[FieldOverrideVO, ...]) -> dict[str, object]:
        """Сериализует ручные значения, сохраняя точность денежной суммы."""
        return {
            str(item.field_id.uuid): {
                "mode": "MANUAL",
                "value": (
                    {"amount": str(item.value.amount)}
                    if isinstance(item.value, PriceAmountVO)
                    else item.value
                ),
            }
            for item in overrides
        }

    @staticmethod
    def to_insert_values(publication: FeedPublication) -> dict[str, object]:
        """Сохраняет Decimal строкой, отличая null, пустую строку и отсутствие записи."""
        return dict(
            id=publication.id.uuid,
            feed_id=publication.feed_id.uuid,
            catalog_item_id=publication.product_reference.catalog_item_id.uuid,
            catalog_variant_id=(
                publication.product_reference.catalog_variant_id.uuid
                if publication.product_reference.catalog_variant_id
                else None
            ),
            status=publication.status.value,
            row_version=publication.version.value,
            created_at=publication.created_at,
            updated_at=publication.updated_at,
            overrides=FeedPublicationMapper.write_overrides(publication.overrides),
        )
