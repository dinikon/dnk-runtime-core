from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from src.modules.tenancy.application.tenant_locale.command.add_tenant_locale.dto import (
    AddTenantLocaleResultDTO,
)
from src.modules.tenancy.application.tenant_locale.query.list_tenant_locales.dto import (
    TenantLocaleDTO,
)


class TenantLocaleResponse(BaseModel):
    """Выбранная локаль и её первоначальный аудит."""

    code: str
    created_at: datetime
    created_by: UUID

    @classmethod
    def from_dto(
        cls, dto: AddTenantLocaleResultDTO | TenantLocaleDTO
    ) -> "TenantLocaleResponse":
        return cls(
            code=dto.code,
            created_at=dto.created_at,
            created_by=dto.created_by,
        )
