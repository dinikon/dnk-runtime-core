from src.modules.files.domain.error import FilesError


class FileStateConflictError(FilesError):
    """Текущее состояние файла не допускает запрошенного перехода."""


class FileTrashExpiredError(FileStateConflictError):
    """Срок восстановления файла из корзины истёк."""
