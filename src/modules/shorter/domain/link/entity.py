from dataclasses import dataclass
from datetime import datetime

from src.modules.shared import EntityIdVO
from ..errors import LinkCodeRequiredError
from .value_object import LinkIdVO


@dataclass(slots=True)
class LinkEntity:
    id: LinkIdVO
    created_at: datetime
    domain_id: EntityIdVO
    code: str

    @classmethod
    def create(
        cls,
        *,
        domain_id: EntityIdVO,
        code: str,
        created_at: datetime,
    ) -> "LinkEntity":
        normalized_code = code.strip()
        if not normalized_code:
            raise LinkCodeRequiredError()
        return cls(
            id=LinkIdVO.new(),
            created_at=created_at,
            domain_id=domain_id,
            code=normalized_code,
        )
