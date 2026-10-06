from src.modules.channels.application.error import ChannelConfigConflictError
from src.modules.channels.domain.error import InvalidChannelError
from src.modules.channels.domain.value_object.settings import ConnectionSettings
from src.modules.channels.application.port.registry import ChannelDefinition
from src.modules.channels.application.port.secret_cipher import SecretCipherPort


def require_writable(definition: ChannelDefinition, version: int) -> None:
    """Проверяет доступность записи и актуальность опубликованной конфигурации."""
    if not definition.can_configure:
        raise InvalidChannelError("Platform configuration is unavailable.")
    if version != definition.config_version:
        raise ChannelConfigConflictError("Configuration changed. Reload the form.")


def seal_settings(
    definition: ChannelDefinition, settings: dict[str, str], cipher: SecretCipherPort
) -> ConnectionSettings:
    """Разделяет публичные и секретные поля схемы и запечатывает credentials."""
    properties = definition.config["connection"]["json_schema"]["properties"]
    secret_names = {k for k, v in properties.items() if v.get("writeOnly")}
    secrets = {k: v for k, v in settings.items() if k in secret_names}
    return ConnectionSettings(
        {k: v for k, v in settings.items() if k not in secret_names},
        cipher.encrypt(secrets),
        tuple(secrets),
    )
