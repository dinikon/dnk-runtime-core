from dataclasses import dataclass

from src.modules.crm.domain.error import CompanyNameRequiredError


@dataclass(frozen=True, slots=True)
class CompanyNameVO:
    value: str

    def __post_init__(self) -> None:
        normalized = self.value.strip()
        if not normalized:
            raise CompanyNameRequiredError()
        object.__setattr__(self, "value", normalized)


__all__ = ["CompanyNameVO"]
