from src.modules.catalog.domain.error import CatalogNotFoundError


class ProductNotFoundError(CatalogNotFoundError):
    """Product отсутствует в текущем tenant."""


class VariantNotFoundError(CatalogNotFoundError):
    """Variant не принадлежит запрошенному Product."""
