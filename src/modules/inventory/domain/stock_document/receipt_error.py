from src.modules.inventory.domain.error import InventoryError


class ReceiptPostingConflictError(InventoryError):
    """Ключ команды поступления уже принадлежит другому намерению."""


class ReceiptFactNotFoundError(InventoryError):
    """Неизменяемый факт не найден в текущем tenant."""
