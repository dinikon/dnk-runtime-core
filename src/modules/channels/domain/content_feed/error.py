from src.modules.shared.domain.domain_error import DomainError


class ContentFeedError(DomainError):
    """Безопасный отказ управления фидом без транспортных деталей."""

    def __init__(self, code: str, *, conflict: bool = False) -> None:
        """Сохраняет стабильную причину и признак конфликта ревизии."""
        super().__init__(code)
        self.code = code
        self.conflict = conflict
