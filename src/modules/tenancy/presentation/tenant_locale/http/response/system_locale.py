from pydantic import BaseModel

from src.modules.tenancy.application.tenant_locale.query.list_system_locales.dto import (
    SystemLocaleDTO,
)


class SystemLocaleResponse(BaseModel):
    """Системная локаль, доступная для выбора."""

    code: str
    name: str

    @classmethod
    def from_dto(cls, dto: SystemLocaleDTO) -> "SystemLocaleResponse":
        return cls(code=dto.code, name=dto.name)
