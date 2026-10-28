"""Общие зависимости внешней сборки Channels."""

from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException

from src.modules.identity.domain.auth.request_context import RequestContext
from src.modules.channels.infrastructure.registry import InstalledPlatforms


def tenant_id_from_context(context: RequestContext) -> UUID:
    """Не допускает сборку tenant-репозитория без workspace."""
    if context.principal is None or not context.principal.tenant_id:
        raise HTTPException(403, detail={"code": "tenant_required"})
    return UUID(context.principal.tenant_id)


def utc_now() -> datetime:
    """Возвращает время внешней границы Channels."""
    return datetime.now(UTC)


def get_platforms() -> InstalledPlatforms:
    """Собирает установленные платформы без сетевых запросов."""
    return InstalledPlatforms()
