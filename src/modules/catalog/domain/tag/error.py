from src.modules.catalog.domain.error import CatalogNotFoundError


class TagNotFoundError(CatalogNotFoundError):
    """Объект tag отсутствует в текущем tenant."""
