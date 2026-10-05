from dataclasses import dataclass

from src.modules.tenancy.domain.tenant_locale.error import InvalidTenantLocaleError
from src.modules.tenancy.domain.tenant_locale.system_locales import (
    SYSTEM_LOCALE_CODES,
)


@dataclass(frozen=True, slots=True)
class TenantLocaleCodeVO:
    """Код локали, разрешённой системным справочником."""

    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or self.value not in SYSTEM_LOCALE_CODES:
            raise InvalidTenantLocaleError("Locale is not available in the system.")
