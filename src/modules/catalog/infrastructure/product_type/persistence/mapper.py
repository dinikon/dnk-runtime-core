from collections.abc import Mapping, Sequence
from typing import Any
from src.modules.catalog.domain.product_type.aggregate import ProductType
from src.modules.catalog.domain.product_type.entity.content_block import ContentBlock
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


class ProductTypeMapper:
    """Преобразует уже прочитанные строки в агрегат без I/O и бизнес-правил."""

    @staticmethod
    def to_domain(
        row: Mapping[str, Any],
        blocks: Sequence[Mapping[str, Any]],
        labels: Sequence[Mapping[str, Any]],
        block_labels: Sequence[Mapping[str, Any]],
    ) -> ProductType:
        """Восстанавливает схему через явные фабрики агрегата и его блоков."""
        return ProductType.restore(
            EntityIdVO(row["id"]),
            row["code"],
            row["schema_version"],
            row["is_system"],
            tuple(
                ContentBlock.restore(
                    EntityIdVO(block["id"]),
                    block["code"],
                    block["value_type"],
                    block["required"],
                    block["position"],
                    {
                        label["locale"]: label["label"]
                        for label in block_labels
                        if label["content_block_id"] == block["id"]
                    },
                )
                for block in blocks
            ),
            {label["locale"]: label["label"] for label in labels},
            EntityIdVO(row["created_by"]),
            EntityIdVO(row["updated_by"]),
            row["created_at"],
            row["updated_at"],
        )

    @staticmethod
    def audit(product_type: ProductType) -> dict[str, Any]:
        """Извлекает общий audit начальной схемы и принадлежащих ей блоков."""
        return dict(
            created_by=product_type.created_by.uuid,
            updated_by=product_type.updated_by.uuid,
            created_at=product_type.created_at,
            updated_at=product_type.updated_at,
            revision=1,
        )
