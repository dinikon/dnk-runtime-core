from src.modules.catalog.domain.error import CatalogNotFoundError


class ProductTypeNotFoundError(CatalogNotFoundError):
    """Запрошенный ProductType отсутствует в текущем tenant."""
