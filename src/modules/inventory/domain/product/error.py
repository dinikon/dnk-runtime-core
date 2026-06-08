from src.modules.shared import DomainError


class ProductNotFoundError(DomainError):
    """Доменная ошибка отсутствующего товара."""

    def __init__(self, product_id: str):
        """Формирует сообщение с id отсутствующего товара."""
        super().__init__(f"Product {product_id} not found")


class InvalidProductSkuError(DomainError):
    """Доменная ошибка некорректного SKU товара."""

    def __init__(self):
        """Формирует сообщение об обязательном SKU."""
        super().__init__("Product SKU must not be empty.")


class InvalidProductNameError(DomainError):
    """Доменная ошибка некорректного названия товара."""

    def __init__(self):
        """Формирует сообщение об обязательном названии товара."""
        super().__init__("Product name must not be empty.")


__all__ = [
    "InvalidProductNameError",
    "InvalidProductSkuError",
    "ProductNotFoundError",
]
