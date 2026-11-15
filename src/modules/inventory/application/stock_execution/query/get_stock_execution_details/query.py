from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class GetStockExecutionDetailsQuery:
    """Задаёт чтение нормализованного факта независимо от идемпотентного ответа."""

    identifier: UUID
