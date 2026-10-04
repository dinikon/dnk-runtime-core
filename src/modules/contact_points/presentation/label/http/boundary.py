from contextlib import contextmanager
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from src.modules.shared.domain.domain_error import DomainError
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.contact_points.domain.label.error import ContactPointLabelNotFoundError
from src.modules.contact_points.infrastructure.persistence.base import (
    ContactPointPersistenceMappingError,
)


def context_ids(context, *, admin=False):
    """Извлекает доверенный tenant и проверяет административные изменения."""
    principal = context.principal
    if principal is None or not principal.tenant_id:
        raise HTTPException(403, "Tenant context is required.")
    if admin and "admin" not in principal.roles:
        raise HTTPException(403, "Требуются права администратора.")
    return EntityIdVO.from_value(principal.tenant_id), EntityIdVO.from_value(
        principal.user_id
    )


@contextmanager
def http_errors():
    """Поднимает HTTP errors, сохраняя rollback внешней UoW."""
    try:
        yield
    except ContactPointLabelNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    except DomainError as exc:
        raise HTTPException(422, str(exc)) from exc
    except IntegrityError as exc:
        raise HTTPException(409, "Конфликт контактных данных.") from exc
    except ContactPointPersistenceMappingError as exc:
        raise HTTPException(500, "Invalid persisted contact point data.") from exc


__all__ = ["context_ids", "http_errors"]
