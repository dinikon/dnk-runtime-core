from dataclasses import dataclass

from src.modules.crm.domain.company.error import InvalidCompanyLegalNameError


@dataclass(slots=True, frozen=True)
class CompanyLegalNameVO:
    """Value object юридического названия CRM-компании."""

    value: str

    def __post_init__(self) -> None:
        """Нормализует и проверяет непустое юридическое название компании."""
        if not isinstance(self.value, str):
            raise InvalidCompanyLegalNameError()
        normalized = self.value.strip()
        if not normalized:
            raise InvalidCompanyLegalNameError()
        object.__setattr__(self, "value", normalized)
