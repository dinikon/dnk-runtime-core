from src.modules.shared.domain.domain_error import DomainError


class FeedBuilderDomainError(DomainError):
    """Описывает нарушение модели FeedBuilder с путём к проблемному значению."""

    def __init__(self, message: str, *, path: tuple[str | int, ...] = ()) -> None:
        """Сохраняет безопасное сообщение и путь без транспортных деталей."""
        super().__init__(message)
        self.path = path
