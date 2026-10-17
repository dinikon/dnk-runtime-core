import base64
from typing import Any
from src.modules.channels.application.publication_import_run.error import (
    PublicationSourceError,
)
from src.modules.channels.application.publication_import_run.port.source import (
    PublicationSourceConnection,
)
from src.modules.channels.infrastructure.publication_import_run.source.http_client import (
    PublicationJsonClient,
)

BASE_URL = "https://api-seller.rozetka.com.ua"


def content(payload: Any) -> dict[str, Any]:
    """Проверяет envelope Rozetka, включая ошибки с HTTP 200, без выдачи их текста."""
    if not isinstance(payload, dict) or type(payload.get("success")) is not bool:
        raise PublicationSourceError("invalid_source_data")
    if payload["success"] is False:
        errors = payload.get("errors")
        errors = errors if isinstance(errors, dict) else {}
        code, message = errors.get("code"), errors.get("message")
        if code in (6001, 1018, 1020, 5401) or message in (
            "session_expired",
            "incorrect_enter_token",
            "invalid_credentials",
        ):
            raise PublicationSourceError("token_expired")
        if code in (1004, 1010) or message in (
            "access_denied",
            "incorrect_username_password",
        ):
            raise PublicationSourceError("access_denied")
        if code in (0, 1003, 5503) or message in (
            "server_error",
            "technical_maintenance",
            "problem_with_message_broker",
        ):
            raise PublicationSourceError("source_unavailable", retryable=True)
        if code in (1019, 5404) or message in ("entity_not_found", "not_found"):
            raise PublicationSourceError("source_item_not_found")
        raise PublicationSourceError("source_request_rejected")
    result = payload.get("content")
    if not isinstance(result, dict):
        raise PublicationSourceError("invalid_source_data")
    return result


class RozetkaSession:
    """Хранит токен только в памяти одной порции, не перенося его в checkpoint."""

    def __init__(
        self, client: PublicationJsonClient, connection: PublicationSourceConnection
    ) -> None:
        """Принимает HTTP адаптер и параметры подключения текущей ревизии."""
        self._client, self._connection = client, connection
        self._token: str | None = None
        self._renewed = False

    async def login(self) -> None:
        """Получает токен по логину и паролю, кодируя пароль только для передачи."""
        username, password = self._connection.public.get(
            "username"
        ), self._connection.secrets.get("password")
        if not username or not username.strip() or not password:
            raise PublicationSourceError("access_denied")
        payload, _ = await self._client.post(
            BASE_URL + "/sites",
            headers={"Content-Language": "uk"},
            payload={
                "username": username,
                "password": base64.b64encode(password.encode()).decode(),
            },
        )
        try:
            token = content(payload).get("access_token")
        except PublicationSourceError as exc:
            if exc.code == "token_expired":
                raise PublicationSourceError("access_denied") from None
            raise
        if (
            not isinstance(token, str)
            or not token.strip()
            or any(c.isspace() for c in token)
        ):
            raise PublicationSourceError("invalid_source_data")
        self._token = token

    async def get(self, path: str, params: dict[str, str | int]) -> dict[str, Any]:
        """Один раз обновляет истёкший токен и повторяет только исходный GET."""
        if self._token is None:
            await self.login()
        assert self._token is not None
        for attempt in range(2):
            try:
                payload, _ = await self._client.get(
                    BASE_URL + path,
                    headers={
                        "Authorization": "Bearer " + self._token,
                        "Content-Language": "uk",
                    },
                    params=params,
                    unauthorized_code="token_expired",
                )
                return content(payload)
            except PublicationSourceError as exc:
                if exc.code != "token_expired":
                    raise
                if self._renewed or attempt:
                    raise PublicationSourceError("access_denied") from None
                self._renewed = True
                await self.login()
        raise PublicationSourceError("access_denied")
