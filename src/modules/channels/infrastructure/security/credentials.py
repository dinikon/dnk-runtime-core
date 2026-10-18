import json
from uuid import UUID
from cryptography.fernet import Fernet, InvalidToken
from src.modules.channels.application.port.plugin_services import PluginCallError
from src.modules.channels.application.plugin_contract import ConnectionCredentialsDTO
from src.modules.channels.domain.error import ChannelsUnavailableError


class ConnectionSecrets:
    """Шифрует credentials с проверяемой привязкой tenant/Connection."""

    def __init__(self, key: str) -> None:
        """Принимает внешний ключ, не сохраняя его в таблицах или логах."""
        self._key = key

    def _cipher(self) -> Fernet:
        """Отказывает явно, если deployment не настроил ключ."""
        if not self._key:
            raise ChannelsUnavailableError("credentials_encryption_not_configured")
        return Fernet(self._key.encode("ascii"))

    def seal(self, tenant_id: UUID, connection_id: UUID, values: dict[str, str]) -> str:
        """Шифрует строго определённый envelope без открытых секретных полей."""
        body = json.dumps(
            {
                "tenant": str(tenant_id),
                "connection": str(connection_id),
                "values": values,
            },
            sort_keys=True,
        )
        return self._cipher().encrypt(body.encode()).decode("ascii")

    def open(
        self, tenant_id: UUID, connection_id: UUID, ciphertext: str
    ) -> ConnectionCredentialsDTO:
        """Отклоняет повреждённый ciphertext и перенос секрета другому владельцу."""
        try:
            body = json.loads(self._cipher().decrypt(ciphertext.encode()))
            if body["tenant"] != str(tenant_id) or body["connection"] != str(
                connection_id
            ):
                raise PluginCallError("credentials_scope_mismatch")
            return ConnectionCredentialsDTO(body["values"])
        except (InvalidToken, ValueError, KeyError, UnicodeError):
            raise PluginCallError("credentials_unavailable") from None


class ScopedCredentialsAccess:
    """Предоставляет плагину только секреты подготовленного сетевого шага."""

    def __init__(
        self,
        secrets: ConnectionSecrets,
        tenant_id: UUID,
        connection_id: UUID,
        ciphertext: str,
    ) -> None:
        """Закрепляет владельца и ciphertext без SQL session."""
        self._secrets, self._tenant, self._connection, self._ciphertext = (
            secrets,
            tenant_id,
            connection_id,
            ciphertext,
        )

    async def resolve(self) -> ConnectionCredentialsDTO:
        """Расшифровывает текущий scoped envelope."""
        return self._secrets.open(self._tenant, self._connection, self._ciphertext)
