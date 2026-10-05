from dataclasses import dataclass
from datetime import datetime
from typing import Self

from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.tenancy.domain.tenant_locale.value_object.code import (
    TenantLocaleCodeVO,
)


@dataclass(frozen=True, slots=True)
class TenantLocale:
    """Локаль, которую tenant выбрал для своего контента."""

    code: TenantLocaleCodeVO
    created_at: datetime
    created_by: EntityIdVO

    @classmethod
    def create(cls, *, code: str, actor_id: EntityIdVO, now: datetime) -> Self:
        """Проверяет код и создаёт выбор локали с аудитом."""
        return cls(TenantLocaleCodeVO(code), now, actor_id)
