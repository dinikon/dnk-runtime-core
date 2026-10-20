from datetime import datetime
from dataclasses import asdict
from typing import Any, Mapping
from uuid import UUID
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.channels.domain.publication_import.aggregate import (
    PublicationImportPreparation,
)
from src.modules.channels.domain.publication_import.value_object.snapshot import (
    ImportSnapshotVO,
    ImportImageVO,
    PreparedImageVO,
)


class PublicationImportMapper:
    """Преобразует persistence и Domain без I/O и исправления инвариантов."""

    @staticmethod
    def to_domain(row: Mapping[str, Any]) -> PublicationImportPreparation:
        """Восстанавливает процесс через явную доменную фабрику."""
        raw = row["snapshot"]
        snapshot = (
            ImportSnapshotVO(
                raw["translations"],
                tuple(ImportImageVO(**image) for image in raw["images"]),
                raw["values"],
                tuple(raw["warnings"]),
                datetime.fromisoformat(raw["read_at"]) if raw.get("read_at") else None,
                (
                    datetime.fromisoformat(raw["source_updated_at"])
                    if raw.get("source_updated_at")
                    else None
                ),
            )
            if raw
            else None
        )
        return PublicationImportPreparation.restore(
            EntityIdVO(row["id"]),
            EntityIdVO(row["publication_id"]),
            EntityIdVO(row["actor_id"]),
            row["connection_generation"],
            row["observed_revision"],
            row["status"],
            row["revision"],
            row["sequence"],
            snapshot,
            {
                key: PreparedImageVO(
                    EntityIdVO(UUID(value["file_id"])) if value["file_id"] else None,
                    value["error_code"],
                )
                for key, value in row["media"].items()
            },
            row["error_code"],
            row["created_at"],
            row["expires_at"],
            tuple(row["used_image_ids"]),
        )

    @staticmethod
    def to_values(preparation: PublicationImportPreparation) -> dict[str, Any]:
        """Сериализует только ограниченные данные процесса и идентификаторы файлов."""
        values = asdict(preparation)
        for name in ("id", "publication_id", "actor_id"):
            values[name] = getattr(preparation, name).uuid
        values["media"] = {
            key: {
                "file_id": str(value.file_id.uuid) if value.file_id else None,
                "error_code": value.error_code,
            }
            for key, value in preparation.media.items()
        }
        if preparation.snapshot:
            for name in ("read_at", "source_updated_at"):
                instant = getattr(preparation.snapshot, name)
                values["snapshot"][name] = instant.isoformat() if instant else None
            values["snapshot"]["schema_version"] = 1
            values["snapshot"]["images"] = list(values["snapshot"]["images"])
            values["snapshot"]["warnings"] = list(values["snapshot"]["warnings"])
        values["used_image_ids"] = list(preparation.used_image_ids)
        return values
