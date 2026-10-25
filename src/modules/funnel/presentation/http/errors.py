from uuid import UUID
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from src.modules.identity.domain.auth.request_context import RequestContext
from src.modules.funnel.domain.error import FunnelConflictError, FunnelNotFoundError


def funnel_identity(context: RequestContext) -> tuple[UUID, UUID]:
    """Воронками управляет любой аутентифицированный пользователь tenant."""
    p = context.principal
    if p is None or not p.tenant_id:
        raise HTTPException(403, "Требуется tenant.")
    return UUID(p.tenant_id), UUID(p.user_id)


def funnel_http_error(error: Exception) -> HTTPException:
    """Переводит ожидаемые ошибки без раскрытия SQL."""
    if isinstance(error, (FunnelConflictError, IntegrityError)):
        return HTTPException(
            409,
            (
                "Конфликт определения."
                if isinstance(error, IntegrityError)
                else str(error)
            ),
        )
    if isinstance(error, FunnelNotFoundError):
        return HTTPException(404, "Воронка не найдена.")
    return HTTPException(422, str(error))
