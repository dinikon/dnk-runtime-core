from src.modules.shared import DomainError


class CategoryNotFoundError(DomainError):
    """Доменная ошибка отсутствующей категории товаров."""

    def __init__(self, category_id: str):
        """Формирует сообщение с id отсутствующей категории."""
        super().__init__(f"Product category {category_id} not found")


class InvalidCategoryNameError(DomainError):
    """Доменная ошибка некорректного имени категории."""

    def __init__(self):
        """Формирует сообщение об обязательном названии категории."""
        super().__init__("Product category name must not be empty.")


class CategoryHierarchyError(DomainError):
    """Доменная ошибка некорректной иерархии категорий."""


__all__ = [
    "CategoryHierarchyError",
    "CategoryNotFoundError",
    "InvalidCategoryNameError",
]
