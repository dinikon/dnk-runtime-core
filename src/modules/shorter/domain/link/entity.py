from dataclasses import dataclass
from datetime import UTC, datetime

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
        domain_id: EntityIdVO,
        code: str,
        created_at: datetime | None = None,
    ) -> "LinkEntity":
        normalized_code = code.strip()
        if not normalized_code:
            raise LinkCodeRequiredError()

        now = created_at or datetime.now(UTC)
        return cls(
            id=LinkIdVO.new(),
            created_at=now,
            domain_id=domain_id,
            code=normalized_code,
        )
