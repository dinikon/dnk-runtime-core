from src.modules.shared.domain.domain_error import DomainError


class CatalogBindingError(DomainError):
    """Безопасная ошибка правил сопоставления."""

    def __init__(self, code: str, *, conflict: bool = False) -> None:
        """Сохраняет публичный код без payload площадки."""
        self.code, self.conflict = code, conflict
        super().__init__(code)
