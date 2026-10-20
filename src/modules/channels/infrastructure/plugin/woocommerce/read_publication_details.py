from src.modules.channels.application.plugin_contract import (
    ReadPublicationDetailsInputDTO,
    ReadPublicationDetailsOutcomeDTO,
    PublicationTranslationDTO,
)
from src.modules.channels.application.port.plugin_services import (
    PluginCredentialsAccess,
    PluginHttpTransport,
    PluginCallError,
)
from src.modules.channels.infrastructure.plugin.woocommerce.manifest import WooSettings
from src.modules.channels.infrastructure.plugin.woocommerce.core_normalizer import (
    normalize_product,
)
from src.modules.channels.infrastructure.plugin.woocommerce.verify_connection import (
    authorization,
)
from src.modules.channels.infrastructure.plugin.core_normalizer import native_id
from src.modules.channels.infrastructure.plugin.content_normalizer import (
    content_body,
    gallery,
)


class WooReadPublicationDetailsPlugin:
    """Читает штатный Woo товар или вариацию на единственной настроенной локали."""

    def __init__(
        self, credentials: PluginCredentialsAccess, http: PluginHttpTransport
    ) -> None:
        """Получает scoped фасады без доступа к чужим repositories."""
        self.credentials, self.http = credentials, http

    async def execute(
        self, request: ReadPublicationDetailsInputDTO
    ) -> ReadPublicationDetailsOutcomeDTO:
        """Для вариации явно наследует отсутствующее содержимое родителя с предупреждением."""
        if not request.external_id.isdecimal() or request.resource_type not in (
            "product",
            "variation",
        ):
            raise PluginCallError("unsupported_publication_type")
        parent_id = request.provider_context.get("parent_id")
        parent_external_id = (
            str(parent_id)
            if isinstance(parent_id, int)
            and not isinstance(parent_id, bool)
            and parent_id > 0
            else None
        )
        headers = await authorization(self.credentials)
        path = "/wp-json/wc/v3/products/"
        parent = None
        if request.resource_type == "variation":
            if not parent_external_id or not parent_external_id.isdecimal():
                raise PluginCallError("publication_parent_missing")
            parent_response = await self.http.get(
                path + parent_external_id, headers=headers
            )
            parent = parent_response.body
            if (
                not isinstance(parent, dict)
                or native_id(parent.get("id")) != parent_external_id
            ):
                raise PluginCallError("invalid_publication_parent")
            path += parent_external_id + "/variations/"
        response = await self.http.get(path + request.external_id, headers=headers)
        row = response.body
        if not isinstance(row, dict) or native_id(row.get("id")) != request.external_id:
            raise PluginCallError("invalid_publication_identity")
        normalized = normalize_product(
            row,
            request.settings,
            int(parent_external_id) if parent is not None else None,
        )
        warnings = list(normalized.core.warnings)
        title, body = normalized.core.title, content_body(row.get("description"))
        images = (
            [row["image"]]
            if isinstance(row.get("image"), dict)
            else row.get("images", [])
        )
        if parent is not None:
            if not title:
                title = normalize_product(parent, request.settings).core.title
                warnings.append("title_inherited_from_parent")
            if not body:
                body = content_body(parent.get("description"))
                warnings.append("description_inherited_from_parent")
            if not images:
                images = parent.get("images", [])
                warnings.append("gallery_inherited_from_parent")
        if not isinstance(images, list) or any(not isinstance(i, dict) for i in images):
            raise PluginCallError("invalid_publication_gallery")
        settings = WooSettings.model_validate(request.settings.options)
        return ReadPublicationDetailsOutcomeDTO(
            normalized.core,
            (PublicationTranslationDTO(settings.locales[0], title, body),),
            gallery(
                [
                    (i.get("id", n), i.get("src"), i.get("alt"))
                    for n, i in enumerate(images)
                ]
            ),
            tuple(warnings),
        )
