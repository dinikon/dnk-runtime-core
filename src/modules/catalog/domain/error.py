from src.modules.shared.domain.domain_error import DomainError


class CatalogError(DomainError):
    """Предметная ошибка с необязательными именами некорректных разделов."""

    def __init__(self, message: str, fields: tuple[str, ...] = ()) -> None:
        """Сохраняет безопасное сообщение и предметные поля для внешнего контракта."""
        super().__init__(message)
        self.fields = fields


class CatalogNotFoundError(CatalogError):
    """Объект отсутствует в текущем tenant."""


class CatalogConflictError(CatalogError):
    """Изменение нарушает уникальность или существующие связи."""


class InvalidCatalogValueError(CatalogError):
    """Значение не соответствует правилам Catalog."""


class CatalogDependencyUnavailableError(CatalogError):
    """Операция требует ещё не подключённого контракта."""
