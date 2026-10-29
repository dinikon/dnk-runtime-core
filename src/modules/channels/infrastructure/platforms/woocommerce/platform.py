from src.modules.channels.infrastructure.platforms.woocommerce.details import (
    WooDetailsReader,
)
from src.modules.channels.application.external_publication.catalog_details import (
    PublicationLookup,
    PublicationDetails,
)
import base64
import json

from pydantic import ValidationError

from src.modules.channels.application.error import VerificationFailure
from src.modules.channels.application.sync_run.port.source import (
    PublicationCheckpoint,
    PublicationObservation,
    PublicationPage,
)
from src.modules.channels.domain.external_publication.value_object import (
    PublicationKind,
)
from src.modules.channels.infrastructure.platforms.woocommerce.publications import (
    WooPublicationReader,
)
from src.modules.channels.application.error import ChannelInputError
from src.modules.channels.application.port.platform import (
    PlatformManifest,
    ValidatedConnection,
)
from src.modules.channels.domain.types import JsonObject
from src.modules.channels.domain.channel.value_object.connection_config import (
    ConnectionConfigVO,
)
from src.modules.channels.domain.channel.value_object.resource_identity import (
    ResourceIdentityVO,
)
from src.modules.channels.infrastructure.http import JsonHttp
from src.modules.channels.infrastructure.platforms.url import normalize_endpoint
from src.modules.channels.infrastructure.platforms.woocommerce.models import (
    WooCommerceConfig,
    WooCommerceCredentials,
    WooSystemStatus,
)


class WooCommercePlatform:
    """Подтверждает доступ защищённым metadata endpoint WooCommerce."""

    def __init__(self, http: JsonHttp) -> None:
        """Собирает явную декларацию и HTTP-порт WooCommerce."""
        self.http = http
        self.manifest = PlatformManifest(
            kind="woocommerce",
            title="WooCommerce",
            config_version=1,
            config_schema=WooCommerceConfig.model_json_schema(),
            credentials_schema=WooCommerceCredentials.model_json_schema(),
            supported_capabilities=("verify_connection", "publications"),
            publication_parent_kind=PublicationKind.VARIABLE,
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

    async def read_publications(
        self,
        *,
        config: ConnectionConfigVO,
        credentials: bytes,
        checkpoint: PublicationCheckpoint,
        parent_external_id: str | None = None,
    ) -> PublicationPage:
        """Восстанавливает конкретные настройки и читает один шаг источника."""
        return await WooPublicationReader(self.http).read(
            config=self.decode_config(config),
            credentials=WooCommerceCredentials.model_validate_json(credentials),
            checkpoint=checkpoint,
            parent_external_id=parent_external_id,
        )

    async def read_publication_dependencies(
        self,
        *,
        config: ConnectionConfigVO,
        credentials: bytes,
        keys: tuple[tuple[str, str], ...],
    ) -> tuple[PublicationObservation, ...]:
        """Дозагружает подтверждённые зависимости изменения структуры."""
        if keys:
            raise VerificationFailure("publication_structure_changed")
        return ()

    async def get_details(
        self,
        *,
        config: ConnectionConfigVO,
        credentials: bytes,
        publications: tuple[PublicationLookup, ...],
    ) -> PublicationDetails:
        """Восстанавливает конкретные типы пакета и читает полное семейство."""
        return await WooDetailsReader(self.http).read(
            config=self.decode_config(config),
            credentials=WooCommerceCredentials.model_validate_json(credentials),
            publications=publications,
        )
