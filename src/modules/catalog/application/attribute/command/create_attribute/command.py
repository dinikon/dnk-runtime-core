from dataclasses import dataclass

from src.modules.shared.domain.value_object.entity_id import EntityIdVO


@dataclass(frozen=True, slots=True)
class CreateAttributeContent:
    locale: str
    name: str


@dataclass(frozen=True, slots=True)
class CreateAttributeOption:
    code: str
    contents: tuple[CreateAttributeContent, ...] = ()


@dataclass(frozen=True, slots=True)
class CreateAttributeCommand:
    actor_id: EntityIdVO
    code: str
    options: tuple[CreateAttributeOption, ...]
    contents: tuple[CreateAttributeContent, ...] = ()
