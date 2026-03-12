from dataclasses import dataclass

from modules.shared import EntityIdVO
from modules.shorter.domain.link.value_object import LinkIdVO


@dataclass(slots=True)
class LinkEntity:
    id: LinkIdVO
    created_at: str
    domain_id: EntityIdVO
    code: str
