from typing import Protocol
from src.modules.channels.application.plugin_contract import (
    VerifyConnectionInputDTO,
    VerifyConnectionOutcomeDTO,
)


class VerifyConnectionPlugin(Protocol):
    """Определяет read-only проверку одного внешнего ресурса."""

    async def execute(
        self, request: VerifyConnectionInputDTO
    ) -> VerifyConnectionOutcomeDTO:
        """Проверяет доступ и identity без SQL и планирования jobs."""
        ...
