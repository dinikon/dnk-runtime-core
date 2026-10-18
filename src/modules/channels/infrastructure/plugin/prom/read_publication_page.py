from src.modules.channels.application.plugin_contract import (
    ReadPublicationPageInputDTO,
    ReadPublicationPageOutcomeDTO,
)
from src.modules.channels.application.port.plugin_services import (
    PluginCredentialsAccess,
    PluginHttpTransport,
    PluginCallError,
)
from src.modules.channels.infrastructure.plugin.core_normalizer import native_id
from src.modules.channels.infrastructure.plugin.prom.core_normalizer import (
    normalize_product,
)


class PromReadPublicationPagePlugin:
    """Обходит страницы групп, затем товары каждой группы одним GET за шаг."""

    def __init__(
        self, credentials: PluginCredentialsAccess, http: PluginHttpTransport
    ) -> None:
        """Принимает scoped credentials и transport без repositories."""
        self.credentials, self.http = (credentials, http)

    async def execute(
        self, request: ReadPublicationPageInputDTO
    ) -> ReadPublicationPageOutcomeDTO:
        """Хранит group/product cursors явно и не объявляет первую страницу полным обходом."""
        state = dict(request.checkpoint) or {
            "version": 1,
            "stage": "groups",
            "groups": [int(request.resource_identity.split(":", 1)[1])],
            "last_id": None,
        }
        if state.get("version") != 1 or state.get("stage") not in (
            "groups",
            "products",
            "complete",
        ):
            raise PluginCallError("checkpoint_version_unsupported")
        if state["stage"] == "complete":
            return ReadPublicationPageOutcomeDTO((), state, True)
        secrets = await self.credentials.resolve()
        headers = {"Authorization": "Bearer " + secrets.values["token"]}
        query = {"limit": "100"}
        if state.get("last_id") is not None:
            query["last_id"] = str(state["last_id"])
        groups = list(state["groups"])
        if state["stage"] == "groups":
            response = await self.http.get(
                "/api/v1/groups/list", query=query, headers=headers
            )
            rows = (
                response.body.get("groups") if isinstance(response.body, dict) else None
            )
            if not isinstance(rows, list):
                raise PluginCallError("invalid_provider_response")
            if len(rows) > 100:
                raise PluginCallError("page_size_limit_exceeded")
            ids = [
                int(native_id(row.get("id"))) for row in rows if isinstance(row, dict)
            ]
            if len(ids) != len(rows):
                raise PluginCallError("invalid_group_identity")
            if ids:
                if state.get("last_id") is not None and max(ids) > int(
                    state["last_id"]
                ):
                    raise PluginCallError("cursor_did_not_advance")
                groups = list(dict.fromkeys([*groups, *ids]))
                if len(groups) > 100000:
                    raise PluginCallError("group_scope_too_large")
                state.update(groups=groups, last_id=min(ids) - 1)
            else:
                state.update(stage="products", group_index=0, last_id=None)
            return ReadPublicationPageOutcomeDTO((), state, False)
        index = int(state["group_index"])
        query["group_id"] = str(groups[index])
        response = await self.http.get(
            "/api/v1/products/list", query=query, headers=headers
        )
        rows = (
            response.body.get("products") if isinstance(response.body, dict) else None
        )
        if not isinstance(rows, list):
            raise PluginCallError("invalid_provider_response")
        if len(rows) > 100:
            raise PluginCallError("page_size_limit_exceeded")
        if not rows:
            index += 1
            complete = index >= len(groups)
            state.update(
                stage="complete" if complete else "products",
                group_index=index,
                last_id=None,
            )
            return ReadPublicationPageOutcomeDTO((), state, complete)
        result, ids, invalid = ([], [], 0)
        for row in rows:
            try:
                if not isinstance(row, dict):
                    raise PluginCallError("invalid_publication_identity")
                identifier = int(native_id(row.get("id")))
                ids.append(identifier)
                result.append(normalize_product(row, request.settings))
            except PluginCallError:
                invalid += 1
        if not ids:
            raise PluginCallError("page_has_no_valid_identity")
        if state.get("last_id") is not None and max(ids) > int(state["last_id"]):
            raise PluginCallError("cursor_did_not_advance")
        state["last_id"] = min(ids) - 1
        return ReadPublicationPageOutcomeDTO(tuple(result), state, False, invalid)
