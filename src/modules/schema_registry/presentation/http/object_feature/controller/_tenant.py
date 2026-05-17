from fastapi import HTTPException, status

from src.modules.shared import EntityIdVO
from src.modules.shared.depends.authentication import AuthenticatedRequestContextDep


def tenant_id_from_context(context: AuthenticatedRequestContextDep) -> EntityIdVO:
    """Возвращает tenant id из authenticated context."""
    principal = context.principal
    if principal is None or principal.tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized.",
        )
    return EntityIdVO.from_value(principal.tenant_id)


__all__ = ["tenant_id_from_context"]
