from dataclasses import dataclass, field
from datetime import datetime
import re

from src.modules.channels.domain.content_media.error import ContentMediaError
from src.modules.channels.domain.content_media.value_object import MediaTransferStatus
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


@dataclass(slots=True)
class ContentMedia:
    """Владеет доступом к версии изображения и соответствием внешнему media ID."""

    id: EntityIdVO
    connection_id: EntityIdVO
    file_id: EntityIdVO
    source_fingerprint: str
    metadata_fingerprint: str
    revision: int
    access_token_hash: bytes = field(repr=False)
    access_token_encrypted: bytes = field(repr=False)
    access_revoked_at: datetime | None
    remote_media_id: str | None
    transfer_status: MediaTransferStatus
    current_operation_id: EntityIdVO | None
    error_code: str | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def create(
        cls,
        *,
        identifier: EntityIdVO,
        connection_id: EntityIdVO,
        file_id: EntityIdVO,
        source_fingerprint: str,
        metadata_fingerprint: str,
        token_hash: bytes,
        token_encrypted: bytes,
        requires_transfer: bool,
        now: datetime,
    ) -> "ContentMedia":
        """Создаёт доступ с первой ревизией без придуманного внешнего ID."""
        if type(requires_transfer) is not bool:
            raise ContentMediaError("media_state_invalid")
        return cls.restore(
            identifier=identifier,
            connection_id=connection_id,
            file_id=file_id,
            source_fingerprint=source_fingerprint,
            metadata_fingerprint=metadata_fingerprint,
            revision=1,
            token_hash=token_hash,
            token_encrypted=token_encrypted,
            access_revoked_at=None,
            remote_media_id=None,
            transfer_status=(
                MediaTransferStatus.PENDING
                if requires_transfer
                else MediaTransferStatus.NOT_REQUIRED
            ),
            current_operation_id=None,
            error_code=None,
            created_at=now,
            updated_at=now,
        )

    @classmethod
    def restore(
        cls,
        *,
        identifier: EntityIdVO,
        connection_id: EntityIdVO,
        file_id: EntityIdVO,
        source_fingerprint: str,
        metadata_fingerprint: str,
        revision: int,
        token_hash: bytes,
        token_encrypted: bytes,
        access_revoked_at: datetime | None,
        remote_media_id: str | None,
        transfer_status: MediaTransferStatus,
        current_operation_id: EntityIdVO | None,
        error_code: str | None,
        created_at: datetime,
        updated_at: datetime,
    ) -> "ContentMedia":
        """Проверяет состояние целиком, не исправляя повреждённые записи."""
        if (
            any(
                not isinstance(value, EntityIdVO)
                for value in (identifier, connection_id, file_id)
            )
            or type(revision) is not int
            or revision < 1
            or any(
                not isinstance(value, str)
                or re.fullmatch(r"[0-9a-f]{64}", value) is None
                for value in (source_fingerprint, metadata_fingerprint)
            )
            or not isinstance(token_hash, bytes)
            or len(token_hash) != 32
            or not isinstance(token_encrypted, bytes)
            or not token_encrypted
            or not isinstance(transfer_status, MediaTransferStatus)
            or (
                current_operation_id is not None
                and not isinstance(current_operation_id, EntityIdVO)
            )
            or (
                remote_media_id is not None
                and (
                    not isinstance(remote_media_id, str) or not remote_media_id.strip()
                )
            )
            or (
                error_code is not None
                and (
                    not isinstance(error_code, str)
                    or re.fullmatch(r"[a-z][a-z0-9_]{0,99}", error_code) is None
                )
            )
        ):
            raise ContentMediaError("media_state_invalid")
        if (
            any(
                not isinstance(value, datetime) or value.utcoffset() is None
                for value in (created_at, updated_at)
            )
            or updated_at < created_at
            or (
                access_revoked_at is not None
                and (
                    not isinstance(access_revoked_at, datetime)
                    or access_revoked_at.utcoffset() is None
                    or not created_at <= access_revoked_at <= updated_at
                )
            )
        ):
            raise ContentMediaError("media_audit_invalid")
        busy = transfer_status in (
            MediaTransferStatus.IN_FLIGHT,
            MediaTransferStatus.UNKNOWN,
        )
        if (
            busy != (current_operation_id is not None)
            or (transfer_status is MediaTransferStatus.READY)
            != (remote_media_id is not None)
            or (
                transfer_status
                in (MediaTransferStatus.UNKNOWN, MediaTransferStatus.FAILED)
            )
            != (error_code is not None)
        ):
            raise ContentMediaError("media_state_invalid")
        return cls(
            identifier,
            connection_id,
            file_id,
            source_fingerprint,
            metadata_fingerprint,
            revision,
            token_hash,
            token_encrypted,
            access_revoked_at,
            remote_media_id,
            transfer_status,
            current_operation_id,
            error_code,
            created_at,
            updated_at,
        )

    def require_revision(self, expected_revision: int) -> None:
        """Отклоняет устаревшую операцию до любого перехода."""
        if type(expected_revision) is not int or expected_revision != self.revision:
            raise ContentMediaError("media_revision_conflict", conflict=True)

    def revoke(self, *, expected_revision: int, now: datetime) -> None:
        """Идемпотентно отзывает URL, сохраняя подтверждённый внешний ID."""
        self.require_revision(expected_revision)
        if self.access_revoked_at is None:
            self._change(
                revoked_at=now,
                remote_id=self.remote_media_id,
                status=(
                    MediaTransferStatus.UNKNOWN
                    if self.transfer_status is MediaTransferStatus.IN_FLIGHT
                    else self.transfer_status
                ),
                operation=self.current_operation_id,
                error=(
                    "media_access_revoked"
                    if self.transfer_status is MediaTransferStatus.IN_FLIGHT
                    else self.error_code
                ),
                now=now,
            )

    def renew_access(
        self,
        *,
        expected_revision: int,
        token_hash: bytes,
        token_encrypted: bytes,
        now: datetime,
    ) -> None:
        """Явно заменяет токен; старый URL больше не принимается."""
        self.require_revision(expected_revision)
        candidate = self.restore(
            identifier=self.id,
            connection_id=self.connection_id,
            file_id=self.file_id,
            source_fingerprint=self.source_fingerprint,
            metadata_fingerprint=self.metadata_fingerprint,
            revision=self.revision + 1,
            token_hash=token_hash,
            token_encrypted=token_encrypted,
            access_revoked_at=None,
            remote_media_id=self.remote_media_id,
            transfer_status=self.transfer_status,
            current_operation_id=self.current_operation_id,
            error_code=self.error_code,
            created_at=self.created_at,
            updated_at=now,
        )
        if now < self.updated_at:
            raise ContentMediaError("media_audit_invalid")
        self.access_token_hash = candidate.access_token_hash
        self.access_token_encrypted = candidate.access_token_encrypted
        self.access_revoked_at = None
        self.revision = candidate.revision
        self.updated_at = candidate.updated_at

    def begin_transfer(
        self, *, expected_revision: int, operation_id: EntityIdVO, now: datetime
    ) -> bool:
        """Резервирует один вариант; неизвестный исход запрещает слепую повторную загрузку."""
        self.require_revision(expected_revision)
        if self.access_revoked_at is not None:
            raise ContentMediaError("media_access_revoked", conflict=True)
        if self.transfer_status is MediaTransferStatus.READY:
            return False
        if self.transfer_status not in (
            MediaTransferStatus.PENDING,
            MediaTransferStatus.FAILED,
        ):
            raise ContentMediaError("media_transfer_unresolved", conflict=True)
        self._change(
            revoked_at=None,
            remote_id=None,
            status=MediaTransferStatus.IN_FLIGHT,
            operation=operation_id,
            error=None,
            now=now,
        )
        return True

    def record_result(
        self,
        *,
        expected_revision: int,
        operation_id: EntityIdVO,
        remote_id: str | None,
        error: str | None,
        uncertain: bool,
        now: datetime,
    ) -> bool:
        """Применяет только текущую операцию; запоздавший результат остаётся no-op."""
        if type(expected_revision) is not int or expected_revision != self.revision:
            return False
        if self.current_operation_id != operation_id or self.transfer_status not in (
            MediaTransferStatus.IN_FLIGHT,
            MediaTransferStatus.UNKNOWN,
        ):
            return False
        status = (
            MediaTransferStatus.READY
            if remote_id is not None
            else (
                MediaTransferStatus.UNKNOWN if uncertain else MediaTransferStatus.FAILED
            )
        )
        self._change(
            revoked_at=self.access_revoked_at,
            remote_id=remote_id,
            status=status,
            operation=operation_id if status is MediaTransferStatus.UNKNOWN else None,
            error=error,
            now=now,
        )
        return True

    def invalidate_remote(self, *, expected_revision: int, now: datetime) -> None:
        """Сбрасывает подтверждённо исчезнувший attachment перед новой передачей."""
        self.require_revision(expected_revision)
        if self.transfer_status is not MediaTransferStatus.READY:
            raise ContentMediaError("media_transfer_unresolved", conflict=True)
        self._change(
            revoked_at=self.access_revoked_at,
            remote_id=None,
            status=MediaTransferStatus.PENDING,
            operation=None,
            error=None,
            now=now,
        )

    def _change(
        self,
        *,
        revoked_at: datetime | None,
        remote_id: str | None,
        status: MediaTransferStatus,
        operation: EntityIdVO | None,
        error: str | None,
        now: datetime,
    ) -> None:
        """Проверяет кандидат до атомарного изменения полей и ревизии."""
        candidate = self.restore(
            identifier=self.id,
            connection_id=self.connection_id,
            file_id=self.file_id,
            source_fingerprint=self.source_fingerprint,
            metadata_fingerprint=self.metadata_fingerprint,
            revision=self.revision + 1,
            token_hash=self.access_token_hash,
            token_encrypted=self.access_token_encrypted,
            access_revoked_at=revoked_at,
            remote_media_id=remote_id,
            transfer_status=status,
            current_operation_id=operation,
            error_code=error,
            created_at=self.created_at,
            updated_at=now,
        )
        if now < self.updated_at:
            raise ContentMediaError("media_audit_invalid")
        self.access_revoked_at = candidate.access_revoked_at
        self.remote_media_id = candidate.remote_media_id
        self.transfer_status = candidate.transfer_status
        self.current_operation_id = candidate.current_operation_id
        self.error_code = candidate.error_code
        self.revision = candidate.revision
        self.updated_at = candidate.updated_at
