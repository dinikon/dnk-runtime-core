from src.modules.files.domain.error import FilesError


class FileStateConflictError(FilesError):
    """Текущее состояние файла не допускает запрошенного перехода."""


class FileTrashExpiredError(FileStateConflictError):
    """Срок восстановления файла из корзины истёк."""


class FileInUseError(FileStateConflictError):
    """Живые ссылки или передача потребителя запрещают удаление файла."""
