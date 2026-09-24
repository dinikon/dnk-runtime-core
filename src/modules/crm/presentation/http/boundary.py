from contextlib import contextmanager
from dataclasses import fields, is_dataclass

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

from src.modules.crm.domain.company.error import CompanyNotFoundError
from src.modules.crm.domain.contact.error import ContactNotFoundError
from src.modules.crm.infrastructure.persistence.base import (
    CrmPersistenceMappingError,
)
from src.modules.shared.domain.domain_error import DomainError
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


def context_ids(context):
    """Извлекает tenant и actor только из доверенного request context."""
    principal = context.principal
    if principal is None or not principal.tenant_id:
        raise HTTPException(403, "Tenant context is required.")
    return EntityIdVO.from_value(principal.tenant_id), EntityIdVO.from_value(
        principal.user_id
    )


def dto_values(value):
    """Рекурсивно преобразует application DTO/VO в HTTP primitives."""
    if isinstance(value, EntityIdVO):
        return value.uuid
    if is_dataclass(value):
        return {
            field.name: dto_values(getattr(value, field.name))
            for field in fields(value)
        }
    if isinstance(value, (tuple, list)):
        return [dto_values(item) for item in value]
    if isinstance(value, dict):
        return {key: dto_values(item) for key, item in value.items()}
    return value


@contextmanager
def http_errors():
    """Переводит CRM domain/infrastructure errors в стабильные HTTP-ответы."""
    try:
        yield
    except (ContactNotFoundError, CompanyNotFoundError) as exc:
        raise HTTPException(404, str(exc)) from exc
    except DomainError as exc:
        raise HTTPException(422, str(exc)) from exc
    except IntegrityError as exc:
        raise HTTPException(409, "Concurrent CRM data conflict.") from exc
    except CrmPersistenceMappingError as exc:
        raise HTTPException(500, "Invalid persisted CRM data.") from exc


__all__ = ["context_ids", "dto_values", "http_errors"]
