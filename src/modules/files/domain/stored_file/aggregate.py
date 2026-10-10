from dataclasses import dataclass
from datetime import datetime
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.files.domain.error import InvalidFileError
from src.modules.files.domain.value_object.file_name import FileNameVO
from src.modules.files.domain.value_object.file_size import FileSizeVO


@dataclass(slots=True)
class StoredFile:
    """Файл с неизменяемым ключом хранения и явным подтверждением загрузки."""

    id: EntityIdVO
    bucket_id: EntityIdVO
    object_key: str
    name: FileNameVO
    content_type: str
    size: FileSizeVO
    status: str
    created_at: datetime

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
        """Создаёт регистрацию загрузки, не перезаписывая существующие объекты."""
        cls._validate(content_type, "uploading", created_at)
        return cls(
            file_id,
            bucket_id,
            file_id.uuid.hex,
            name,
            content_type,
            size,
            "uploading",
            created_at,
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
        status: str,
        created_at: datetime,
    ) -> "StoredFile":
        """Восстанавливает файл с проверкой состояния и ключа."""
        cls._validate(content_type, status, created_at)
        if object_key != file_id.uuid.hex:
            raise InvalidFileError("Invalid object key.")
        return cls(
            file_id, bucket_id, object_key, name, content_type, size, status, created_at
        )

    @staticmethod
    def _validate(content_type: str, status: str, created_at: datetime) -> None:
        """Проверяет технические метаданные и допустимое состояние файла."""
        if (
            not content_type
            or len(content_type) > 255
            or "/" not in content_type
            or any(ord(c) < 32 or ord(c) == 127 for c in content_type)
        ):
            raise InvalidFileError("Invalid content type.")
        if status not in {"uploading", "ready"} or created_at.tzinfo is None:
            raise InvalidFileError("Invalid file state.")

    def mark_uploaded(self, actual_size: int) -> None:
        """Подтверждает загрузку только при совпадении фактического размера."""
        if self.status != "uploading" or actual_size != self.size.value:
            raise InvalidFileError("File length does not match metadata.")
        self.status = "ready"
