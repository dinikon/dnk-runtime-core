from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


@dataclass(slots=True, frozen=True)
class ContactPointInputDTO:
    """Черновик контактной строки на границе CRM."""

    candidate_point_id: EntityIdVO
    candidate_binding_id: EntityIdVO
    value: str
    binding_id: EntityIdVO | None = None
    label_id: EntityIdVO | None = None
    country_code: str | None = None


@dataclass(slots=True, frozen=True)
class ContactPointDTO:
    """Данные строки CRM без внутренних типов contact_points."""

    binding_id: EntityIdVO
    contact_point_id: EntityIdVO
    value: str
    label_id: EntityIdVO | None
    country_code: str | None


@dataclass(slots=True, frozen=True)
class ContactPointsDTO:
    """Два независимых контактных списка карточки."""

    phones: tuple[ContactPointDTO, ...] = ()
    emails: tuple[ContactPointDTO, ...] = ()


class ContactPointsPort(Protocol):
    """Потребности CRM; транзакцией и проверкой target владеет вызывающий use case."""

    async def sync(
        self,
        tenant_id: EntityIdVO,
        actor_id: EntityIdVO,
        model_key: str,
        record_id: EntityIdVO,
        phones: tuple[ContactPointInputDTO, ...] | None,
        emails: tuple[ContactPointInputDTO, ...] | None,
    ) -> None: ...
    async def get_many(
        self, tenant_id: EntityIdVO, model_key: str, record_ids: tuple[EntityIdVO, ...]
    ) -> Mapping[EntityIdVO, ContactPointsDTO]: ...
    async def remove(
        self, tenant_id: EntityIdVO, model_key: str, record_id: EntityIdVO
    ) -> None: ...


__all__ = [
    "ContactPointInputDTO",
    "ContactPointDTO",
    "ContactPointsDTO",
    "ContactPointsPort",
]
