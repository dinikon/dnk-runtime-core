import json
from pydantic import ValidationError
from src.modules.channels.application.error import (
    ChannelInputError,
    VerificationFailure,
)
from src.modules.channels.application.port.platform import (
    PlatformManifest,
    ValidatedConfig,
)
from src.modules.channels.domain.error import InvalidResourceIdentityError
from src.modules.channels.domain.value_object.connection_config import (
    ConnectionConfigVO,
)
from src.modules.channels.domain.value_object.resource_identity import (
    ResourceIdentityVO,
)
from src.modules.channels.domain.types import JsonObject
from src.modules.channels.infrastructure.http import JsonHttp
from src.modules.channels.infrastructure.platforms.rozetka.models import (
    RozetkaConfig,
    RozetkaCredentials,
    RozetkaLogin,
)


class RozetkaPlatform:
    """Проверяет настройки и доступ к магазину Rozetka."""

    def __init__(self, http: JsonHttp) -> None:
        """Связывает конкретные модели и verifier с общим transport."""
        self.http = http
        self.manifest = PlatformManifest(
            kind="rozetka",
            title="Rozetka",
            config_version=1,
            config_schema=RozetkaConfig.model_json_schema(),
            credentials_schema=RozetkaCredentials.model_json_schema(),
            supported_capabilities=("verify_connection",),
        )

    def decode_config(self, config: ConnectionConfigVO) -> RozetkaConfig:
        """Восстанавливает конкретную модель настроек Rozetka."""
        return RozetkaConfig.model_validate(
            {
                "version": config.version,
                "endpoint": config.endpoint,
                "settings": config.settings,
            }
        )

    def validate_config(self, config: ConnectionConfigVO) -> ValidatedConfig:
        """Проверяет и нормализует публичные настройки платформы."""
        try:
            typed = self.decode_config(config)
        except ValidationError as error:
            path = error.errors(include_input=False)[0]["loc"]
            location = (
                str(path[0])
                if path and path[0] in {"version", "endpoint", "settings"}
                else ""
            )
            raise ChannelInputError(
                "configuration_invalid",
                field="config" + ("." + location if location else ""),
            ) from None
        return ValidatedConfig(
            config=ConnectionConfigVO.create(
                version=typed.version,
                endpoint=typed.endpoint,
                settings=typed.settings.model_dump(mode="json"),
            ),
            currency=typed.settings.currency,
            locales=typed.settings.locales,
        )

    def encode_credentials(self, credentials: JsonObject) -> bytes:
        """Сериализует полный комплект реальных секретов для Shared Cipher."""
        try:
            secret = RozetkaCredentials.model_validate(credentials)
        except ValidationError as error:
            path = error.errors(include_input=False)[0]["loc"]
            location = str(path[0]) if path and path[0] in {"token"} else ""
            raise ChannelInputError(
                "credentials_invalid",
                field="credentials" + ("." + location if location else ""),
            ) from None
        return json.dumps(
            {"token": secret.token.get_secret_value()},
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")

    async def verify(
        self, config: ConnectionConfigVO, credentials: bytes
    ) -> ResourceIdentityVO:
        """Получает identity по постоянному токену без парольной авторизации."""
        try:
            settings = self.decode_config(config)
            secret = RozetkaCredentials.model_validate_json(credentials)
            data = await self.http.request(
                "GET",
                settings.endpoint + "/sites/get-auth-data",
                headers={"Authorization": "Bearer " + secret.token.get_secret_value()},
            )
            response = RozetkaLogin.model_validate(data)
            if not response.success:
                raise VerificationFailure("invalid_credentials")
            if response.content is None:
                raise VerificationFailure("resource_identity_unavailable")
            return ResourceIdentityVO(
                namespace="rozetka.market", key=str(response.content.market.id)
            )
        except ValidationError:
            raise VerificationFailure("provider_response_invalid") from None
        except InvalidResourceIdentityError:
            raise VerificationFailure("resource_identity_unavailable") from None
