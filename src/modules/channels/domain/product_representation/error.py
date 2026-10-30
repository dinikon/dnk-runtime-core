from src.modules.shared.domain.domain_error import DomainError


class ProductRepresentationError(DomainError):
    """Безопасный отказ правил представления без HTTP и полей формы."""

    def __init__(self, code: str, *, conflict: bool = False) -> None:
        """Сохраняет стабильную причину и признак конфликта состояния."""
        super().__init__(code)
        self.code = code
        self.conflict = conflict
