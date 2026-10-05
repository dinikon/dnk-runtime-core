from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from src.modules.tenancy.domain.tenant_locale.value_object.code import (
    TenantLocaleCodeVO,
)


@dataclass(frozen=True, slots=True)
class TenantLocaleRecord:
    """Проекция выбранной локали без восстановления агрегата."""

    code: str
    created_at: datetime
    created_by: UUID


class TenantLocaleQueryRepositoryProtocol(Protocol):
    """Читает справочник только из текущей tenant-схемы."""

    async def list_all(self) -> list[TenantLocaleRecord]: ...

    async def contains(self, code: TenantLocaleCodeVO) -> bool: ...
