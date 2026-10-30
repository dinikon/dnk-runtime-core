from src.modules.shared.domain.domain_error import DomainError


class ContentMediaError(DomainError):
    """Безопасный отказ подготовки, доступа или передачи изображения."""

    def __init__(self, code: str, *, conflict: bool = False) -> None:
        """Сохраняет причину без URL, токенов и ответов площадки."""
        super().__init__(code)
        self.code = code
        self.conflict = conflict
