from src.modules.shared.domain.domain_error import DomainError


class InvalidContentBlockError(DomainError):
    """Определение блока или его перевод нарушает доменные правила."""


class ContentBlockNotFoundError(DomainError):
    """Определение блока отсутствует в текущем tenant."""


class ContentBlockConflictError(DomainError):
    """Системный или используемый блок нельзя изменить либо удалить."""
