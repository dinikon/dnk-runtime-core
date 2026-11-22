from typing import Protocol
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SchemaLocaleDTO:
    """Передаёт доступную локаль без зависимости от моделей справочника."""

    code: str
    name: str


class SchemaLocalesPort(Protocol):
    """Читает поддержанные локали одним запросом через владельца справочника."""

    async def list_available(self) -> tuple[SchemaLocaleDTO, ...]:
        """Возвращает активные нормализованные коды и подписи."""
        ...
