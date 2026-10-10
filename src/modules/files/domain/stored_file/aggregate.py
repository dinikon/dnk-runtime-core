from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.files.domain.error import InvalidFileError
from src.modules.files.domain.stored_file.error import (
    FileStateConflictError,
    FileTrashExpiredError,
)
from src.modules.files.domain.stored_file.status import StoredFileStatus
from src.modules.files.domain.value_object.file_name import FileNameVO
from src.modules.files.domain.value_object.file_size import FileSizeVO


@dataclass(slots=True)
class StoredFile:
    """Файл с неизменяемым ключом, корзиной и подтверждаемым удалением."""

    id: EntityIdVO
    bucket_id: EntityIdVO
    object_key: str
    name: FileNameVO
    content_type: str
    size: FileSizeVO
    status: StoredFileStatus
    created_at: datetime
    deleted_at: datetime | None = None
    deleted_by: EntityIdVO | None = None
    purge_after: datetime | None = None
    purge_requested_at: datetime | None = None
    purge_job_id: EntityIdVO | None = None

    @classmethod
    def create(
        cls,
        *,
        file_id: EntityIdVO,
        bucket_id: EntityIdVO,
        name: FileNameVO,
        content_type: str,
        size: FileSizeVO,
        created_at: datetime,
    ) -> "StoredFile":
        """Создаёт регистрацию загрузки без данных корзины."""
        return cls.restore(
            file_id=file_id,
            bucket_id=bucket_id,
            object_key=file_id.uuid.hex,
            name=name,
            content_type=content_type,
            size=size,
            status=StoredFileStatus.UPLOADING,
            created_at=created_at,
        )

    @classmethod
    def restore(
        cls,
        *,
        file_id: EntityIdVO,
        bucket_id: EntityIdVO,
        object_key: str,
        name: FileNameVO,
        content_type: str,
        size: FileSizeVO,
        status: StoredFileStatus | str,
        created_at: datetime,
        deleted_at: datetime | None = None,
        deleted_by: EntityIdVO | None = None,
        purge_after: datetime | None = None,
        purge_requested_at: datetime | None = None,
        purge_job_id: EntityIdVO | None = None,
    ) -> "StoredFile":
        """Восстанавливает только целостное состояние с временем в UTC."""
        try:
            restored_status = StoredFileStatus(status)
        except ValueError as error:
            raise InvalidFileError("Invalid file status.") from error
        aggregate = cls(
            id=file_id,
            bucket_id=bucket_id,
            object_key=object_key,
            name=name,
            content_type=content_type,
            size=size,
            status=restored_status,
            created_at=cls._utc(created_at),
            deleted_at=cls._utc(deleted_at) if deleted_at is not None else None,
            deleted_by=deleted_by,
            purge_after=cls._utc(purge_after) if purge_after is not None else None,
            purge_requested_at=(
                cls._utc(purge_requested_at) if purge_requested_at is not None else None
            ),
            purge_job_id=purge_job_id,
        )
        aggregate._validate_state()
        return aggregate

    @staticmethod
    def _utc(value: datetime) -> datetime:
        """Отклоняет время без часового пояса и нормализует его в UTC."""
        if not isinstance(value, datetime) or value.utcoffset() is None:
            raise InvalidFileError("File timestamps must be timezone-aware.")
        return value.astimezone(UTC)

    def _validate_state(self) -> None:
        """Проверяет ключ, метаданные и комбинации полей жизненного цикла."""
        if self.object_key != self.id.uuid.hex:
            raise InvalidFileError("Invalid object key.")
        if (
            not self.content_type
            or len(self.content_type) > 255
            or "/" not in self.content_type
            or any(ord(c) < 32 or ord(c) == 127 for c in self.content_type)
        ):
            raise InvalidFileError("Invalid content type.")
        trash = (self.deleted_at, self.deleted_by, self.purge_after)
        purge = (self.purge_requested_at, self.purge_job_id)
        if self.status in {StoredFileStatus.UPLOADING, StoredFileStatus.READY}:
            if any(value is not None for value in (*trash, *purge)):
                raise InvalidFileError("Active files cannot have trash metadata.")
            return
        if any(value is None for value in trash):
            raise InvalidFileError("Trash metadata is required.")
        if not isinstance(self.deleted_by, EntityIdVO):
            raise InvalidFileError("Trash actor must be an entity ID.")
        if (
            self.deleted_at < self.created_at
            or self.purge_after != self.deleted_at + timedelta(days=30)
        ):
            raise InvalidFileError("Invalid trash retention timestamps.")
        if self.status == StoredFileStatus.TRASHED:
            if any(value is not None for value in purge):
                raise InvalidFileError("Trashed files cannot have a purge job.")
        elif (
            any(value is None for value in purge)
            or not isinstance(self.purge_job_id, EntityIdVO)
            or self.purge_requested_at < self.deleted_at
        ):
            raise InvalidFileError("Invalid purge metadata.")

    def _operation_time(self, now: datetime) -> datetime:
        """Не позволяет переходу предшествовать уже записанным событиям."""
        value = self._utc(now)
        previous = self.purge_requested_at or self.deleted_at or self.created_at
        if value < previous:
            raise FileStateConflictError("File transition cannot move time backwards.")
        return value

    def mark_uploaded(self, actual_size: int) -> None:
        """Подтверждает загрузку только при совпадении фактического размера."""
        if self.status != StoredFileStatus.UPLOADING or actual_size != self.size.value:
            raise InvalidFileError("File length does not match metadata.")
        self.status = StoredFileStatus.READY

    def move_to_trash(self, actor_id: EntityIdVO, now: datetime) -> None:
        """Переносит готовый файл в корзину на 720 часов без продления при повторе."""
        instant = self._operation_time(now)
        if self.status == StoredFileStatus.TRASHED:
            return
        if self.status != StoredFileStatus.READY:
            raise FileStateConflictError("Only ready files can be moved to trash.")
        if not isinstance(actor_id, EntityIdVO):
            raise InvalidFileError("Trash actor must be an entity ID.")
        self.deleted_at = instant
        self.deleted_by = actor_id
        self.purge_after = instant + timedelta(days=30)
        self.status = StoredFileStatus.TRASHED

    def restore_from_trash(self, now: datetime) -> None:
        """Восстанавливает файл строго до истечения срока хранения корзины."""
        instant = self._operation_time(now)
        if self.status == StoredFileStatus.READY:
            return
        if self.status != StoredFileStatus.TRASHED:
            raise FileStateConflictError("Only trashed files can be restored.")
        if instant >= self.purge_after:
            raise FileTrashExpiredError("File trash retention has expired.")
        self.deleted_at = None
        self.deleted_by = None
        self.purge_after = None
        self.status = StoredFileStatus.READY

    def request_purge(self, now: datetime, job_id: EntityIdVO) -> None:
        """Фиксирует ручное удаление и сохраняет исходную job при повторе."""
        instant = self._operation_time(now)
        if self.status == StoredFileStatus.PURGING:
            return
        if self.status != StoredFileStatus.TRASHED:
            raise FileStateConflictError("Only trashed files can be purged.")
        if not isinstance(job_id, EntityIdVO):
            raise InvalidFileError("Purge job must be an entity ID.")
        self.purge_requested_at = instant
        self.purge_job_id = job_id
        self.status = StoredFileStatus.PURGING

    def request_expired_purge(self, now: datetime, job_id: EntityIdVO) -> None:
        """Разрешает автоматическое удаление только после 720 часов хранения."""
        instant = self._operation_time(now)
        if self.status == StoredFileStatus.PURGING:
            return
        if self.status != StoredFileStatus.TRASHED:
            raise FileStateConflictError("Only trashed files can be purged.")
        if instant < self.purge_after:
            raise FileStateConflictError("File trash retention has not expired.")
        self.request_purge(instant, job_id)

    def replace_purge_job(self, job_id: EntityIdVO) -> None:
        """Назначает замену остановившейся job без изменения сроков корзины."""
        if self.status != StoredFileStatus.PURGING:
            raise FileStateConflictError("Only purging files can replace a purge job.")
        if not isinstance(job_id, EntityIdVO):
            raise InvalidFileError("Purge job must be an entity ID.")
        self.purge_job_id = job_id

    def is_current_purge_job(self, job_id: EntityIdVO) -> bool:
        """Проверяет принадлежность доставки текущей операции удаления."""
        return self.status == StoredFileStatus.PURGING and self.purge_job_id == job_id

    def mark_purged(self, job_id: EntityIdVO) -> None:
        """Подтверждает физическое удаление только текущей job."""
        if self.status == StoredFileStatus.PURGED and self.purge_job_id == job_id:
            return
        if not self.is_current_purge_job(job_id):
            raise FileStateConflictError("Purge job is no longer current.")
        self.status = StoredFileStatus.PURGED

    def ensure_purged(self) -> None:
        """Запрещает удаление регистрации до подтверждения физического удаления."""
        if self.status != StoredFileStatus.PURGED:
            raise FileStateConflictError("File purge has not been confirmed.")
