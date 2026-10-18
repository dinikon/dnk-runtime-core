from src.modules.channels.application.plugin_contract import (
    VerifyConnectionInputDTO,
    VerifyConnectionOutcomeDTO,
)
from src.modules.channels.application.port.plugin_services import (
    PluginCredentialsAccess,
    PluginHttpTransport,
    PluginCallError,
)
from src.modules.channels.infrastructure.plugin.core_normalizer import native_id


class PromVerifyConnectionPlugin:
    """Проверяет чтение и закрепляет identity корневой группы компании Prom."""

    def __init__(
        self, credentials: PluginCredentialsAccess, http: PluginHttpTransport
    ) -> None:
        """Принимает только scoped фасады SDK."""
        self.credentials, self.http = (credentials, http)

    async def execute(
        self, request: VerifyConnectionInputDTO
    ) -> VerifyConnectionOutcomeDTO:
        """Разрешает нулевой scope списка товаров в настоящую корневую группу."""
        secrets = await self.credentials.resolve()
        headers = {"Authorization": "Bearer " + secrets.values["token"]}
        result = await self.http.get(
            "/api/v1/products/list",
            query={"limit": "1"},
            headers=headers,
        )
        if not isinstance(result.body, dict) or not isinstance(
            result.body.get("products"), list
        ):
            raise PluginCallError("invalid_provider_response")
        group_id = result.body.get("group_id")
        if type(group_id) is int and group_id == 0:
            groups = await self.http.get(
                "/api/v1/groups/list", query={"limit": "100"}, headers=headers
            )
            rows = groups.body.get("groups") if isinstance(groups.body, dict) else None
            if not isinstance(rows, list) or any(
                not isinstance(row, dict) for row in rows
            ):
                raise PluginCallError("invalid_provider_response")
            if len(rows) > 100:
                raise PluginCallError("page_size_limit_exceeded")
            roots = [
                row
                for row in rows
                if "parent_group_id" in row and row["parent_group_id"] is None
            ]
            if len(roots) != 1:
                raise PluginCallError("resource_identity_unavailable")
            group_id = roots[0].get("id")
        root = native_id(group_id)
        return VerifyConnectionOutcomeDTO(
            "root_group:" + root, limitations=("api_visible_statuses_only",)
        )
