from datetime import datetime
from decimal import Decimal
from typing import Any, Mapping
from uuid import UUID
from src.modules.channels.application.publication_import.query.get_publication_import.dto import (
    GetPublicationImportResultDTO,
    PublicationImportImagePreviewDTO,
)
from src.modules.channels.application.product_representation.contracts import (
    CatalogDraftValuesDTO,
)


class PublicationImportQueryMapper:
    """Создаёт проекцию предпросмотра, не вызывая фабрики агрегатов."""

    @staticmethod
    def to_details(row: Mapping[str, Any]) -> GetPublicationImportResultDTO:
        """Явно преобразует JSON decimals и результаты переноса файлов."""
        snapshot = row["snapshot"]
        values = None
        translations, images, warnings = {}, [], ()
        if snapshot is not None:
            translations = snapshot["translations"]
            raw = snapshot["values"]
            values = CatalogDraftValuesDTO(
                {code: text["title"] or "" for code, text in translations.items()},
                raw["sku"],
                (
                    Decimal(raw["regular_price"])
                    if raw["regular_price"] is not None
                    else None
                ),
                Decimal(raw["sale_price"]) if raw["sale_price"] is not None else None,
                raw["currency"],
                raw["manage_stock"],
                Decimal(raw["quantity"]) if raw["quantity"] is not None else None,
                raw["stock_status"],
                raw["backorders"],
                {code: text["body"] or "" for code, text in translations.items()},
                tuple(image["id"] for image in snapshot["images"]),
                snapshot["images"][0]["id"] if snapshot["images"] else None,
            )
            for image in snapshot["images"]:
                result = row["media"][image["id"]]
                images.append(
                    PublicationImportImagePreviewDTO(
                        image["id"],
                        UUID(result["file_id"]) if result["file_id"] else None,
                        image["alt"],
                        result["error_code"],
                    )
                )
            warnings = tuple(snapshot["warnings"])
        return GetPublicationImportResultDTO(
            row["id"],
            row["publication_id"],
            row["actor_id"],
            row["status"],
            row["revision"],
            row["observed_revision"],
            row["created_at"],
            row["expires_at"],
            row["error_code"],
            values,
            translations,
            tuple(images),
            warnings,
            row["sequence"],
            (
                datetime.fromisoformat(snapshot["read_at"])
                if snapshot and snapshot.get("read_at")
                else None
            ),
        )
