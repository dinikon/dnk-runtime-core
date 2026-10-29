class PublicationCatalogError(Exception):
    """Безопасная ошибка координации создания из публикации."""

    def __init__(self, code: str, *, conflict: bool = False) -> None:
        """Не содержит response, credentials или SQL."""
        self.code, self.conflict = code, conflict
        super().__init__(code)


class PublicationCatalogSkuRace(PublicationCatalogError):
    """Позволяет один ограниченный повтор после конфликта уникальности SKU."""
