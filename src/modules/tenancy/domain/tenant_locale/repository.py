from typing import Protocol

from src.modules.tenancy.domain.tenant_locale.aggregate import TenantLocale
from src.modules.tenancy.domain.tenant_locale.value_object.code import (
    TenantLocaleCodeVO,
)


class TenantLocaleRepositoryProtocol(Protocol):
    """Сохраняет выбранные локали в текущей tenant-схеме внешнего UoW."""

    async def add(self, locale: TenantLocale) -> None: ...

    async def remove(self, code: TenantLocaleCodeVO) -> bool: ...
