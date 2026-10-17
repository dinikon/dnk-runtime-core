from src.modules.catalog.domain.error import CatalogNotFoundError


class AttributeNotFoundError(CatalogNotFoundError):
    """Определение характеристики отсутствует в текущем tenant."""
