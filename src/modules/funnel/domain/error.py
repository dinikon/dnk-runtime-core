from src.modules.shared.domain.domain_error import DomainError


class FunnelError(DomainError):
    """Нарушены правила определения процесса."""


class FunnelNotFoundError(FunnelError):
    """Процесс или стадия недоступны."""


class FunnelConflictError(FunnelError):
    """Определение процесса изменилось конкурентно."""
