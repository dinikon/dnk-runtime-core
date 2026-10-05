from src.modules.shared.domain.domain_error import DomainError


class InvalidCategoryError(DomainError):
    """Нарушены правила дерева или переводов категории."""


class CategoryLocaleUnavailableError(DomainError):
    """Локаль отсутствует в активном глобальном справочнике."""


class CategoryNotFoundError(DomainError):
    """Категория отсутствует в текущем tenant."""


class CategoryCycleError(DomainError):
    """Перенос категории создаёт цикл."""


class CategoryInUseError(DomainError):
    """Категорию нельзя удалить, пока она используется."""


class CategoryIdentifierAlreadyExistsError(DomainError):
    """Идентификатор категории уже занят."""
