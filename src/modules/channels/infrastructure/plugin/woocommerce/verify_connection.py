import base64
from src.modules.channels.application.plugin_contract import (
    VerifyConnectionInputDTO,
    VerifyConnectionOutcomeDTO,
)
from src.modules.channels.application.port.plugin_services import (
    PluginCredentialsAccess,
    PluginHttpTransport,
    PluginCallError,
)


async def authorization(credentials: PluginCredentialsAccess) -> dict[str, str]:
    """Создаёт Basic header только для HTTPS scoped transport."""
    values = (await credentials.resolve()).values
    token = base64.b64encode(
        (values["consumer_key"] + ":" + values["consumer_secret"]).encode()
    ).decode("ascii")
    return {"Authorization": "Basic " + token}


class WooVerifyConnectionPlugin:
    """Проверяет административное чтение и канонический адрес сайта."""

    def __init__(
        self, credentials: PluginCredentialsAccess, http: PluginHttpTransport
    ) -> None:
        """Принимает только scoped фасады SDK."""
        self.credentials, self.http = (credentials, http)

    async def execute(
        self, request: VerifyConnectionInputDTO
    ) -> VerifyConnectionOutcomeDTO:
        """Читает публичный WordPress root и проверяет ключи только на Woo endpoint."""
        root = await self.http.get("/wp-json/")
        if not isinstance(root.body, dict) or not isinstance(root.body.get("url"), str):
            raise PluginCallError("resource_identity_unavailable")
        canonical = root.body["url"].rstrip("/")
        if canonical != request.settings.endpoint:
            raise PluginCallError("resource_endpoint_mismatch")
        headers = await authorization(self.credentials)
        products = await self.http.get(
            "/wp-json/wc/v3/products",
            query={"per_page": "1", "status": "any"},
            headers=headers,
        )
        if not isinstance(products.body, list):
            raise PluginCallError("invalid_provider_response")
        return VerifyConnectionOutcomeDTO(
            "site:" + canonical, limitations=("api_visible_statuses_only",)
        )
