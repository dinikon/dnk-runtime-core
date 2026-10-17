from enum import StrEnum


class StoredFileStatus(StrEnum):
    """Состояния регистрации, корзины и подтверждённого удаления файла."""

    UPLOADING = "uploading"
    READY = "ready"
    TRASHED = "trashed"
    PURGING = "purging"
    PURGED = "purged"
