from src.modules.catalog.domain.error import CatalogNotFoundError


class ContentBlockNotFoundError(CatalogNotFoundError):
    """Запрошенный ContentBlock отсутствует в текущем tenant."""
