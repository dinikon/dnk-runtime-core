import base64
import json
from pydantic import ValidationError
from src.modules.channels.application.error import ChannelInputError
from src.modules.channels.application.port.platform import (
    PlatformManifest,
    ValidatedConnection,
)
from src.modules.channels.domain.value_object.connection_config import (
    ConnectionConfigVO,
)
from src.modules.channels.domain.value_object.resource_identity import (
    ResourceIdentityVO,
)
from src.modules.channels.domain.types import JsonObject
from src.modules.channels.infrastructure.http import JsonHttp
from src.modules.channels.infrastructure.platforms.url import normalize_endpoint
from src.modules.channels.infrastructure.platforms.woocommerce.models import (
    WooCommerceConfig,
    WooCommerceCredentials,
    WooSystemStatus,
)


class WooCommercePlatform:
    """Проверяет настройки и доступ к магазину WooCommerce."""

    def __init__(self, http: JsonHttp) -> None:
        """Связывает конкретные модели и verifier с общим transport."""
        self.http = http
        self.manifest = PlatformManifest(
            kind="woocommerce",
            title="WooCommerce",
            config_version=1,
            config_schema=WooCommerceConfig.model_json_schema(),
            credentials_schema=WooCommerceCredentials.model_json_schema(),
            supported_capabilities=("verify_connection",),
        )

    def decode_config(self, config: ConnectionConfigVO) -> WooCommerceConfig:
        """Восстанавливает конкретную модель настроек WooCommerce."""
        return WooCommerceConfig.model_validate(
            {
                "version": config.version,
                "endpoint": config.endpoint,
                "settings": config.settings,
            }
        )

    def validate(
        self, config: ConnectionConfigVO, credentials: JsonObject | None
    ) -> ValidatedConnection:
        """Проверяет настройки и явно сериализует полный комплект credentials."""
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
        encoded = None
        if credentials is not None:
            try:
                secret = WooCommerceCredentials.model_validate(credentials)
            except ValidationError as error:
                path = error.errors(include_input=False)[0]["loc"]
                location = (
                    str(path[0])
                    if path and path[0] in {"consumer_key", "consumer_secret"}
                    else ""
                )
                raise ChannelInputError(
                    "credentials_invalid",
                    field="credentials" + ("." + location if location else ""),
                ) from None
            encoded = json.dumps(
                {
                    "consumer_key": secret.consumer_key.get_secret_value(),
                    "consumer_secret": secret.consumer_secret.get_secret_value(),
                },
                ensure_ascii=False,
                separators=(",", ":"),
            ).encode("utf-8")
        return ValidatedConnection(
            config=ConnectionConfigVO.create(
                version=typed.version,
                endpoint=typed.endpoint,
                settings=typed.settings.model_dump(mode="json"),
            ),
            credentials=encoded,
            currency=typed.settings.currency,
            locales=(typed.settings.locale,),
        )

    async def verify(
        self, config: ConnectionConfigVO, credentials: bytes
    ) -> ResourceIdentityVO:
        """Определяет canonical identity, сохраняя секреты в заголовке Basic."""
        settings = self.decode_config(config)
        secret = WooCommerceCredentials.model_validate_json(credentials)
        basic = base64.b64encode(
            (
                secret.consumer_key.get_secret_value()
                + ":"
                + secret.consumer_secret.get_secret_value()
            ).encode()
        ).decode()
        data = await self.http.request(
            "GET",
            settings.endpoint + "/wp-json/wc/v3/system_status",
            headers={"Authorization": "Basic " + basic},
        )
        response = WooSystemStatus.model_validate(data)
        return ResourceIdentityVO(
            namespace="woocommerce.site",
            key=normalize_endpoint(response.environment.site_url),
        )
