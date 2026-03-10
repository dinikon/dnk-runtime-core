from dataclasses import dataclass
from typing import ClassVar, Self

from src.modules.crm.domain.error import (
    ProductRowDiscountTypeNotSupportedError,
    ProductRowEntityIdRequiredError,
)
from src.modules.crm.domain.shared.crm_entity_id import CrmEntityIdVO


class ProductRowIdVO(CrmEntityIdVO): ...


@dataclass(frozen=True, slots=True)
class ProductRowEntityIdVO:
    LEAD: ClassVar[int] = 1
    DEAL: ClassVar[int] = 2

    value: int

    def __post_init__(self) -> None:
        if self.value <= 0:
            raise ProductRowEntityIdRequiredError()

    @classmethod
    def lead(cls) -> Self:
        return cls(value=cls.LEAD)

    @classmethod
    def deal(cls) -> Self:
        return cls(value=cls.DEAL)


@dataclass(frozen=True, slots=True)
class ProductRowDiscountTypeVO:
    PERCENT: ClassVar[str] = "PERCENT"
    FIXED: ClassVar[str] = "FIXED"

    value: str

    def __post_init__(self) -> None:
        normalized = self.value.strip().upper()
        if normalized not in {self.PERCENT, self.FIXED}:
            raise ProductRowDiscountTypeNotSupportedError(normalized)
        object.__setattr__(self, "value", normalized)

    @classmethod
    def percent(cls) -> Self:
        return cls(value=cls.PERCENT)

    @classmethod
    def fixed(cls) -> Self:
        return cls(value=cls.FIXED)


__all__ = [
    "ProductRowDiscountTypeVO",
    "ProductRowEntityIdVO",
    "ProductRowIdVO",
]
