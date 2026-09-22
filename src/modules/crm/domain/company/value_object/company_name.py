from dataclasses import dataclass

from src.modules.crm.domain.company.error import InvalidCompanyNameError


@dataclass(slots=True, frozen=True)
class CompanyNameVO:
    """Нормализованное отображаемое название компании."""

    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str):
            raise InvalidCompanyNameError("Company name must be a string.")
        normalized = self.value.strip()
        if not normalized:
            raise InvalidCompanyNameError("Company name must not be empty.")
        if len(normalized) > 255:
            raise InvalidCompanyNameError(
                "Company name must not exceed 255 characters."
            )
        object.__setattr__(self, "value", normalized)


__all__ = ["CompanyNameVO"]
