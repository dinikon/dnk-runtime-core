from src.modules.shared.domain.domain_error import DomainError


class InvalidProductContentError(DomainError):
    """Перевод товара содержит недопустимые значения."""


class InvalidProductLocaleError(DomainError):
    """Код локали товара имеет недопустимый формат."""


class ProductLocaleUnavailableError(DomainError):
    """Локаль отсутствует в активном глобальном справочнике."""


class ProductNotFoundError(DomainError):
    """Товар отсутствует в текущем tenant."""


class ProductSkuNotFoundError(DomainError):
    """Учётная позиция отсутствует в текущем tenant."""


class ProductIdentifierAlreadyExistsError(DomainError):
    """Идентификатор товара или варианта уже занят."""


class InvalidProductVariantError(DomainError):
    """Нарушено правило вариантов и их комбинаций."""


class ProductOptionUnavailableError(DomainError):
    """Выбранный option не принадлежит активному атрибуту Catalog."""
