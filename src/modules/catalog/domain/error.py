from src.modules.shared.domain.domain_error import DomainError


class CatalogError(DomainError):
    """Базовая предметная ошибка Catalog."""


class CatalogNotFoundError(CatalogError):
    """Объект отсутствует в текущем tenant."""


class CatalogConflictError(CatalogError):
    """Ревизия устарела либо изменение нарушает существующие связи."""


class InvalidCatalogValueError(CatalogError):
    """Значение не соответствует правилам Catalog."""


class CatalogDependencyUnavailableError(CatalogError):
    """Операция требует ещё не подключённого контракта."""
