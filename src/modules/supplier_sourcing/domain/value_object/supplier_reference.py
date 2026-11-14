from dataclasses import dataclass
from enum import StrEnum
from typing import Self
from uuid import UUID
from src.modules.supplier_sourcing.domain.value_object.supplier_id import SupplierIdVO
from src.modules.supplier_sourcing.domain.supplier_source.error import (
    InvalidSupplierSourceValueError,
)


class SupplierModelKey(StrEnum):
    """Ограничивает поставщика компанией или контактом CRM."""

    COMPANY = "crm.company"
    CONTACT = "crm.contact"


@dataclass(frozen=True, slots=True)
class SupplierReferenceVO:
    """Полная идентичность поставщика: тип контрагента и его номинальный UUID."""

    model_key: SupplierModelKey
    identifier: SupplierIdVO

    def __post_init__(self) -> None:
        """Отклоняет неполную ссылку и значения чужого контекста."""
        if not isinstance(self.model_key, SupplierModelKey) or not isinstance(
            self.identifier, SupplierIdVO
        ):
            raise InvalidSupplierSourceValueError(
                "Нужны тип контрагента и типизированный идентификатор поставщика."
            )

    @classmethod
    def from_value(cls, model_key: str, identifier: UUID) -> Self:
        """Преобразует публичную пару примитивов в локальную ссылку контекста."""
        try:
            kind = SupplierModelKey(model_key)
        except (ValueError, TypeError) as exc:
            raise InvalidSupplierSourceValueError(
                "Поставщик должен быть компанией или контактом CRM."
            ) from exc
        return cls(kind, SupplierIdVO.from_value(identifier))
