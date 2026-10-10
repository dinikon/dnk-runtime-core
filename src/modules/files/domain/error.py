from src.modules.shared.domain.domain_error import DomainError


class FilesError(DomainError):
    """Базовая предметная ошибка файлового модуля."""


class StorageNotFoundError(FilesError):
    """Подключение или бакет не зарегистрированы в текущем tenant."""


class FileNotFoundError(FilesError):
    """Файл отсутствует или ещё не готов к чтению."""


class InvalidStorageStateError(FilesError):
    """Состояние хранилища не допускает запрошенной операции."""


class InvalidFileError(FilesError):
    """Метаданные или содержимое файла некорректны."""


class SystemProviderImmutableError(FilesError):
    """Пользователь не может изменить системное подключение."""
