from dataclasses import dataclass
from enum import StrEnum
from typing import Self
from uuid import UUID
from src.modules.external_fulfillment.domain.value_object.references import (
    ExternalSupplierIdVO,
)
from src.modules.external_fulfillment.domain.error import (
    InvalidSupplierFulfillmentValueError,
)


class ExternalSupplierModelKey(StrEnum):
    """Ограничивает поставщика компанией или контактом CRM."""

    COMPANY = "crm.company"
    CONTACT = "crm.contact"


@dataclass(frozen=True, slots=True)
class ExternalSupplierReferenceVO:
    """Полная идентичность поставщика: тип контрагента и его номинальный UUID."""

    model_key: ExternalSupplierModelKey
    identifier: ExternalSupplierIdVO

    def __post_init__(self) -> None:
        """Отклоняет неполную ссылку и значения чужого контекста."""
        if not isinstance(self.model_key, ExternalSupplierModelKey) or not isinstance(
            self.identifier, ExternalSupplierIdVO
        ):
            raise InvalidSupplierFulfillmentValueError(
                "Нужны тип контрагента и типизированный идентификатор поставщика."
            )

    @classmethod
    def from_value(cls, model_key: str, identifier: UUID) -> Self:
        """Преобразует публичную пару примитивов в локальную ссылку контекста."""
        try:
            kind = ExternalSupplierModelKey(model_key)
        except (ValueError, TypeError) as exc:
            raise InvalidSupplierFulfillmentValueError(
                "Поставщик должен быть компанией или контактом CRM."
            ) from exc
        return cls(kind, ExternalSupplierIdVO.from_value(identifier))
