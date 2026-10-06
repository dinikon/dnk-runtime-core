from dataclasses import asdict
from decimal import Decimal
from typing import Any, Mapping
from src.modules.channels.domain.external_publication.value_object.read_document import (
    PublicationReadDocumentVO,
    PublicationImageVO,
    PublicationAttributeVO,
    PublicationCategoryVO,
)


class PublicationDocumentMapper:
    """Преобразует версионированные значения документа без I/O и правил платформы."""

    @staticmethod
    def to_values(document: PublicationReadDocumentVO) -> dict[str, Any]:
        """Сериализует Decimal без потери точности и вложенные неизменяемые значения."""
        values = asdict(document)
        for key in ("price", "regular_price", "sale_price", "quantity"):
            values[key] = None if values[key] is None else str(values[key])
        return values

    @staticmethod
    def to_document(values: Mapping[str, Any]) -> PublicationReadDocumentVO:
        """Восстанавливает снимок Read документа для write-side агрегата."""
        data = dict(values)
        for key in ("price", "regular_price", "sale_price", "quantity"):
            data[key] = None if data[key] is None else Decimal(data[key])
        data["images"] = tuple(PublicationImageVO(**row) for row in data["images"])
        data["attributes"] = tuple(
            PublicationAttributeVO(**row) for row in data["attributes"]
        )
        data["categories"] = tuple(
            PublicationCategoryVO(**row) for row in data["categories"]
        )
        data["warnings"] = tuple(data["warnings"])
        return PublicationReadDocumentVO(**data)
