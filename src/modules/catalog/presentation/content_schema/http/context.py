from typing import NoReturn

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

from src.modules.catalog.application.content_schema.service import (
    SchemaConflictError,
    SchemaNotFoundError,
    SchemaValidationError,
)
from src.modules.identity.domain.auth.request_context import RequestContext


def require_tenant(context: RequestContext) -> None:
    if context.principal is None or not context.principal.tenant_id:
        raise HTTPException(403, "Tenant context is required.")


def raise_schema_http_error(exc: Exception) -> NoReturn:
    if isinstance(exc, SchemaNotFoundError):
        raise HTTPException(404, str(exc)) from exc
    if isinstance(exc, (SchemaConflictError, IntegrityError)):
        raise HTTPException(409, str(exc)) from exc
    if isinstance(exc, (SchemaValidationError, ValueError)):
        raise HTTPException(422, str(exc)) from exc
    raise exc
