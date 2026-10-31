import json
from urllib.parse import urlencode
from pydantic import ValidationError
from src.modules.channels.application.error import (
    ChannelInputError,
    VerificationFailure,
)
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
from src.modules.channels.infrastructure.platforms.prom.models import (
    PromConfig,
    PromCredentials,
    PromGroups,
)


class PromPlatform:
    """Проверяет настройки и доступ к магазину Prom."""

    def __init__(self, http: JsonHttp) -> None:
        """Связывает конкретные модели и verifier с общим transport."""
        self.http = http
        self.manifest = PlatformManifest(
            kind="prom",
            title="Prom",
            config_version=1,
            config_schema=PromConfig.model_json_schema(),
            credentials_schema=PromCredentials.model_json_schema(),
            supported_capabilities=("verify_connection",),
        )

    def decode_config(self, config: ConnectionConfigVO) -> PromConfig:
        """Восстанавливает конкретную модель настроек Prom."""
        return PromConfig.model_validate(
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
                secret = PromCredentials.model_validate(credentials)
            except ValidationError as error:
                path = error.errors(include_input=False)[0]["loc"]
                location = str(path[0]) if path and path[0] in {"token"} else ""
                raise ChannelInputError(
                    "credentials_invalid",
                    field="credentials" + ("." + location if location else ""),
                ) from None
            encoded = json.dumps(
                {"token": secret.token.get_secret_value()},
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
            locales=typed.settings.locales,
        )

    async def verify(
        self, config: ConnectionConfigVO, credentials: bytes
    ) -> ResourceIdentityVO:
        """Обходит страницы групп; неоднозначность и неполный обход отклоняются."""
        settings = self.decode_config(config)
        secret = PromCredentials.model_validate_json(credentials)
        seen: set[int] = set()
        roots: set[int] = set()
        last_id = None
        for _ in range(50):
            query = {"limit": 100}
            if last_id is not None:
                query["last_id"] = last_id
            data = await self.http.request(
                "GET",
                settings.endpoint + "/api/v1/groups/list?" + urlencode(query),
                headers={"Authorization": "Bearer " + secret.token.get_secret_value()},
            )
            page = PromGroups.model_validate(data)
            ids = [group.id for group in page.groups]
            if set(ids) & seen or len(ids) != len(set(ids)):
                raise VerificationFailure("resource_identity_unavailable")
            seen.update(ids)
            roots.update(
                group.id
                for group in page.groups
                if group.id > 0 and group.parent_group_id is None
            )
            if len(roots) > 1:
                raise VerificationFailure("resource_identity_unavailable")
            if len(ids) < 100:
                if len(roots) == 1:
                    return ResourceIdentityVO(
                        namespace="prom.root_group", key=str(next(iter(roots)))
                    )
                raise VerificationFailure("resource_identity_unavailable")
            last_id = ids[-1]
        raise VerificationFailure("resource_identity_unavailable")
