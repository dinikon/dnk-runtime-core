from dataclasses import dataclass

from src.modules.shared import EntityIdVO


@dataclass(frozen=True, slots=True)
class ContactPointIdVO(EntityIdVO): ...
