from uuid import UUID


class FeedBuildError(Exception):
    """Безопасный отказ получения или сериализации полного документа."""

    def __init__(
        self,
        code: str,
        *,
        publication_id: UUID | None = None,
        field: str | None = None,
        unavailable: bool = False,
    ) -> None:
        """Не сохраняет исходный URL, XML или текст внешнего исключения."""
        super().__init__(code)
        self.code, self.publication_id, self.field = code, publication_id, field
        self.unavailable = unavailable
