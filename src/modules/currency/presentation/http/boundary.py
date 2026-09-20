from contextlib import contextmanager
from dataclasses import fields, is_dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.shared.domain.value_object.currency import CurrencyCodeVO
from src.modules.shared.domain.domain_error import DomainError
from src.modules.currency.domain.models import ProviderCode
from src.modules.currency.domain.errors import (
    CurrencyConflict,
    CurrencyNotFound,
    CurrencyError,
    ProviderUnavailable,
)

WRITE_PERMISSIONS = (
    "currency.manage_enabled",
    "currency.manage_policy",
    "currency.manage_rates",
    "currency.change_functional_currency",
    "currency.import_rates",
)


def permissions(context):
    principal = context.principal
    if principal is None or not principal.is_authenticated or not principal.tenant_id:
        return []
    return (
        ["currency.view", *WRITE_PERMISSIONS]
        if "admin" in principal.roles
        else (["currency.view"] if "member" in principal.roles else [])
    )


def require(context, permission):
    if permission not in permissions(context):
        raise HTTPException(
            403,
            {
                "code": "currency_forbidden",
                "message": "Currency permission is required.",
            },
        )
    return EntityIdVO.from_value(context.principal.tenant_id), EntityIdVO.from_value(
        context.principal.user_id
    )


def wire(value):
    if isinstance(value, (CurrencyCodeVO, ProviderCode, EntityIdVO, UUID)):
        return str(value)
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return {f.name: wire(getattr(value, f.name)) for f in fields(value)}
    if isinstance(value, dict):
        return {str(k): wire(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [wire(item) for item in value]
    return value


@contextmanager
def currency_errors():
    try:
        yield
    except CurrencyError as exc:
        status = (
            409
            if isinstance(exc, CurrencyConflict)
            else (
                404
                if isinstance(exc, CurrencyNotFound)
                else 503 if isinstance(exc, ProviderUnavailable) else 422
            )
        )
        raise HTTPException(status, {"code": exc.code, "message": str(exc)}) from exc
    except DomainError as exc:
        raise HTTPException(
            422, {"code": getattr(exc, "code", "invalid_money"), "message": str(exc)}
        ) from exc
    except IntegrityError as exc:
        raise HTTPException(
            409,
            {
                "code": "currency_conflict",
                "message": "Concurrent currency change. Reload and retry.",
            },
        ) from exc
