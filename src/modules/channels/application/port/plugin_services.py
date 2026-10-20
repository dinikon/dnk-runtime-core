from typing import Protocol
from src.modules.channels.application.plugin_contract import (
    ConnectionCredentialsDTO,
    HttpResultDTO,
)


class PluginCredentialsAccess(Protocol):
    """Выдаёт только секреты уже выбранного tenant/Connection."""

    async def resolve(self) -> ConnectionCredentialsDTO:
        """Расшифровывает секреты без передачи session плагину."""
        ...


class PluginHttpTransport(Protocol):
    """Выполняет только GET в пределах текущего источника."""

    async def get(
        self,
        path: str,
        *,
        query: dict[str, str] | None = None,
        headers: dict[str, str] | None = None,
    ) -> HttpResultDTO:
        """Возвращает ограниченный по размеру ответ без redirects."""
        ...


class PluginContentHttpTransport(PluginHttpTransport, Protocol):
    """Добавляет ограниченную запись текстов в пределах проверенного origin."""

    async def put(
        self,
        path: str,
        *,
        payload: dict[str, str],
        headers: dict[str, str] | None = None,
    ) -> HttpResultDTO:
        """Передаёт только название и описание без произвольных полей карточки."""
        ...


class PluginCallError(Exception):
    """Передаёт безопасный код сбоя провайдера без URL, body и секретов."""

    def __init__(self, reason_code: str, *, retryable: bool = False) -> None:
        """Сохраняет только стабильный код и разрешение ограниченного retry."""
        super().__init__(reason_code)
        self.reason_code, self.retryable = (reason_code, retryable)
