from zoneinfo import ZoneInfo
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
from src.modules.channels.infrastructure.plugin.prom.manifest import PromSettings
from src.modules.channels.infrastructure.plugin.prom.core_normalizer import (
    normalize_product,
)
from src.modules.channels.infrastructure.plugin.core_normalizer import (
    native_id,
    safe_text,
)
from src.modules.channels.infrastructure.plugin.prom.translations import localized_field
from src.modules.channels.infrastructure.plugin.prom.images import original_image_url
from src.modules.channels.infrastructure.plugin.content_normalizer import (
    content_body,
    gallery,
)
from src.modules.shared.infrastructure.time.utc_clock import UtcClock


class PromReadPublicationDetailsPlugin:
    """Читает товар по native ID и извлекает настроенные языки из multilang."""

    def __init__(
        self, credentials: PluginCredentialsAccess, http: PluginHttpTransport
    ) -> None:
        """Получает только scoped фасады HTTP и credentials."""
        self.credentials, self.http = credentials, http

    async def execute(
        self, request: ReadPublicationDetailsInputDTO
    ) -> ReadPublicationDetailsOutcomeDTO:
        """Закрепляет один ответ REST; X-LANGUAGE не заменяет языковые поля товара."""
        if request.resource_type != "product" or not request.external_id.isdecimal():
            raise PluginCallError("unsupported_publication_type")
        settings = PromSettings.model_validate(request.settings.options)
        credentials = await self.credentials.resolve()
        response = await self.http.get(
            "/api/v1/products/" + request.external_id,
            headers={
                "Authorization": "Bearer " + credentials.values["token"],
                "X-LANGUAGE": settings.locales[0],
            },
        )
        row = response.body.get("product") if isinstance(response.body, dict) else None
        if not isinstance(row, dict) or native_id(row.get("id")) != request.external_id:
            raise PluginCallError("invalid_publication_identity")
        core = normalize_product(
            row,
            request.settings,
            observed_on=UtcClock().now().astimezone(ZoneInfo("Europe/Kyiv")).date(),
        ).core
        warnings = list(core.warnings)
        translations = tuple(
            PublicationTranslationDTO(
                locale,
                safe_text(
                    localized_field(row, "name", locale), 2000, warnings, "title"
                ),
                content_body(localized_field(row, "description", locale)),
            )
            for locale in settings.locales
        )
        base_id = row.get("variation_base_id")
        if row.get("is_variation") is True and any(
            not translation.body for translation in translations
        ):
            if (
                isinstance(base_id, bool)
                or not isinstance(base_id, int)
                or base_id <= 0
                or str(base_id) == request.external_id
            ):
                raise PluginCallError("invalid_publication_parent")
            parent_response = await self.http.get(
                "/api/v1/products/" + str(base_id),
                headers={
                    "Authorization": "Bearer " + credentials.values["token"],
                    "X-LANGUAGE": settings.locales[0],
                },
            )
            parent = (
                parent_response.body.get("product")
                if isinstance(parent_response.body, dict)
                else None
            )
            if (
                not isinstance(parent, dict)
                or not isinstance(parent.get("id"), int)
                or parent.get("id") != base_id
                or isinstance(parent.get("id"), bool)
                or parent.get("is_variation") is True
                or parent.get("variation_group_id") != row.get("variation_group_id")
            ):
                raise PluginCallError("invalid_publication_parent")
            inherited = []
            for translation in translations:
                body = translation.body
                if not body:
                    body = content_body(
                        localized_field(parent, "description", translation.locale)
                    )
                    if body:
                        warnings.append("description_inherited_from_parent")
                inherited.append(
                    PublicationTranslationDTO(
                        translation.locale, translation.title, body
                    )
                )
            translations = tuple(inherited)
        image_rows = []
        if row.get("main_image"):
            image_rows.append(("main", original_image_url(row["main_image"]), ""))
        images = row.get("images", [])
        if not isinstance(images, list) or any(not isinstance(i, dict) for i in images):
            raise PluginCallError("invalid_publication_gallery")
        image_rows.extend(
            (i.get("id", n), original_image_url(i.get("url")), "")
            for n, i in enumerate(images)
        )
        return ReadPublicationDetailsOutcomeDTO(
            core, translations, gallery(image_rows), tuple(dict.fromkeys(warnings))
        )
