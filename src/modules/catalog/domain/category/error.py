from src.modules.catalog.domain.error import CatalogNotFoundError


class CategoryNotFoundError(CatalogNotFoundError):
    """Объект category отсутствует в текущем tenant."""
