from src.modules.channels.application.plugin_contract import (
    ReadPublicationPageInputDTO,
    ReadPublicationPageOutcomeDTO,
)
from src.modules.channels.application.port.plugin_services import (
    PluginCredentialsAccess,
    PluginHttpTransport,
    PluginCallError,
)
from src.modules.channels.infrastructure.plugin.woocommerce.verify_connection import (
    authorization,
)
from src.modules.channels.infrastructure.plugin.woocommerce.core_normalizer import (
    normalize_product,
)
from src.modules.channels.infrastructure.plugin.core_normalizer import native_id


class WooReadPublicationPagePlugin:
    """Читает продукты и variation-потоки одним ограниченным запросом за шаг."""

    def __init__(
        self, credentials: PluginCredentialsAccess, http: PluginHttpTransport
    ) -> None:
        """Принимает scoped credentials и transport."""
        self.credentials, self.http = (credentials, http)

    async def execute(
        self, request: ReadPublicationPageInputDTO
    ) -> ReadPublicationPageOutcomeDTO:
        """Обходит страницы до пустого результата, не ограничиваясь опубликованными."""
        state = dict(request.checkpoint) or {
            "version": 1,
            "page": 1,
            "parents": [],
            "variation_page": 1,
            "last_ids": [],
        }
        if state.get("version") != 1:
            raise PluginCallError("checkpoint_version_unsupported")
        parents = list(state.get("parents", []))
        parent = int(parents[0]) if parents else None
        page = int(state.get("variation_page", 1) if parent else state["page"])
        if page > 100000:
            raise PluginCallError("page_scope_too_large")
        path = (
            f"/wp-json/wc/v3/products/{parent}/variations"
            if parent
            else "/wp-json/wc/v3/products"
        )
        response = await self.http.get(
            path,
            query={
                "per_page": "100",
                "page": str(page),
                "status": "any",
                "orderby": "id",
                "order": "asc",
            },
            headers=await authorization(self.credentials),
        )
        rows = response.body
        if not isinstance(rows, list):
            raise PluginCallError("invalid_provider_response")
        if len(rows) > 100:
            raise PluginCallError("page_size_limit_exceeded")
        if not rows:
            if parent:
                state.update(parents=parents[1:], variation_page=1, variation_ids=[])
                return ReadPublicationPageOutcomeDTO((), state, False)
            state["complete"] = True
            return ReadPublicationPageOutcomeDTO((), state, True)
        ids, result, invalid = ([], [], 0)
        for row in rows:
            try:
                if not isinstance(row, dict):
                    raise PluginCallError("invalid_publication_identity")
                identifier = int(native_id(row.get("id")))
                ids.append(identifier)
                result.append(normalize_product(row, request.settings, parent))
                if not parent and row.get("type") == "variable":
                    parents.append(identifier)
            except PluginCallError:
                invalid += 1
        previous = state.get("variation_ids" if parent else "last_ids", [])
        if not ids or ids == previous or (previous and min(ids) <= max(previous)):
            raise PluginCallError("cursor_did_not_advance")
        if parent:
            state.update(variation_page=page + 1, variation_ids=ids)
        else:
            state.update(page=page + 1, parents=parents, last_ids=ids)
        return ReadPublicationPageOutcomeDTO(tuple(result), state, False, invalid)
