from src.modules.crm.domain.sales_error import SalesError


def sale_text(value: str | None, field: str, *, required: bool = False) -> str | None:
    """Нормализует ограниченный текст карточки, сохраняя отсутствие значения."""
    if value is None and not required:
        return None
    if not isinstance(value, str):
        raise SalesError(f"{field}: ожидается строка.")
    value = value.strip()
    if (required and not value) or len(value) > 255:
        raise SalesError(f"{field}: от 1 до 255 символов.")
    return value or None
