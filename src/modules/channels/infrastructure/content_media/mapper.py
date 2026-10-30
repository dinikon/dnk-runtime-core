from collections.abc import Mapping
from typing import Any

from src.modules.channels.application.content_media.contracts import MediaReadRow
from src.modules.channels.domain.content_media.aggregate import ContentMedia
from src.modules.channels.domain.content_media.value_object import MediaTransferStatus
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


class ContentMediaMapper:
    """Явно разделяет восстановление, запись и безопасную read-проекцию."""

    @staticmethod
    def to_domain(row: Mapping[str, Any]) -> ContentMedia:
        """Передаёт проверку сочетаний полей доменной фабрике."""
        return ContentMedia.restore(
            identifier=EntityIdVO(row["id"]),
            connection_id=EntityIdVO(row["connection_id"]),
            file_id=EntityIdVO(row["file_id"]),
            source_fingerprint=row["source_fingerprint"],
            metadata_fingerprint=row["metadata_fingerprint"],
            revision=row["revision"],
            token_hash=row["access_token_hash"],
            token_encrypted=row["access_token_encrypted"],
            access_revoked_at=row["access_revoked_at"],
            remote_media_id=row["remote_media_id"],
            transfer_status=MediaTransferStatus(row["transfer_status"]),
            current_operation_id=(
                EntityIdVO(row["current_operation_id"])
                if row["current_operation_id"]
                else None
            ),
            error_code=row["error_code"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    @staticmethod
    def to_values(media: ContentMedia) -> dict[str, Any]:
        """Не сохраняет вычисленную галерею или открытый токен."""
        return dict(
            id=media.id.uuid,
            connection_id=media.connection_id.uuid,
            file_id=media.file_id.uuid,
            source_fingerprint=media.source_fingerprint,
            metadata_fingerprint=media.metadata_fingerprint,
            revision=media.revision,
            access_token_hash=media.access_token_hash,
            access_token_encrypted=media.access_token_encrypted,
            access_revoked_at=media.access_revoked_at,
            remote_media_id=media.remote_media_id,
            transfer_status=media.transfer_status.value,
            current_operation_id=(
                media.current_operation_id.uuid if media.current_operation_id else None
            ),
            error_code=media.error_code,
            created_at=media.created_at,
            updated_at=media.updated_at,
        )

    @staticmethod
    def to_projection(row: Mapping[str, Any]) -> MediaReadRow:
        """Читает доступ без восстановления агрегата и расшифровки секретов."""
        return MediaReadRow(
            id=row["id"],
            connection_id=row["connection_id"],
            channel_id=row["channel_id"],
            file_id=row["file_id"],
            source_fingerprint=row["source_fingerprint"],
            metadata_fingerprint=row["metadata_fingerprint"],
            revision=row["revision"],
            access_token_hash=row["access_token_hash"],
            access_revoked_at=row["access_revoked_at"],
            transfer_status=MediaTransferStatus(row["transfer_status"]),
        )
