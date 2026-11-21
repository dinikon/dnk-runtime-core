from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class GetReturnOriginQuery:
    """Запрашивает возможность возврата по одному исходному исполнению."""

    execution_id: UUID
