from dataclasses import dataclass

from src.modules.crm.domain.company.error import InvalidCompanyLegalNameError


@dataclass(frozen=True, slots=True)
class CompanyLegalNameVO:
    """Нормализованное юридическое название компании."""

    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str):
            raise InvalidCompanyLegalNameError("legal_name: ожидается строка.")
        value = self.value.strip()
        if not 1 <= len(value) <= 255:
            raise InvalidCompanyLegalNameError(
                "legal_name: требуется от 1 до 255 символов."
            )
        object.__setattr__(self, "value", value)
