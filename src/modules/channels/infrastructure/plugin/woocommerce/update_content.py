from src.modules.channels.application.content_update.plugin_contract import (
    InspectContentUpdateInputDTO,
    InspectContentUpdateOutcomeDTO,
    SendContentUpdateInputDTO,
    SendContentUpdateOutcomeDTO,
)
from src.modules.channels.application.content_update.texts import content_texts
from src.modules.channels.application.port.plugin_services import (
    PluginCredentialsAccess,
    PluginContentHttpTransport,
    PluginCallError,
)
from src.modules.channels.infrastructure.plugin.woocommerce.read_publication_details import (
    WooReadPublicationDetailsPlugin,
)
from src.modules.channels.infrastructure.plugin.woocommerce.verify_connection import (
    authorization,
)
from src.modules.channels.infrastructure.plugin.woocommerce.manifest import WooSettings


class WooContentUpdatePlugin:
    """Изменяет name/description только существующего товара на одной настроенной локали."""

    def __init__(
        self, credentials: PluginCredentialsAccess, http: PluginContentHttpTransport
    ) -> None:
        """Получает только scoped HTTP и credentials фасады."""
        self.credentials, self.http = credentials, http

    async def inspect(
        self, request: InspectContentUpdateInputDTO
    ) -> InspectContentUpdateOutcomeDTO:
        """Сравнивает точную цель; вариации с наследуемым названием недоступны для записи."""
        settings = WooSettings.model_validate(request.target.settings.options)
        if tuple(text.locale for text in request.desired) != tuple(settings.locales):
            raise PluginCallError("content_update_locales_mismatch")
        details = await WooReadPublicationDetailsPlugin(
            self.credentials, self.http
        ).execute(request.target)
        issues = []
        if request.target.resource_type != "product":
            issues.append("content_update_target_unsupported")
        if any(not text.title or not text.body for text in request.desired):
            issues.append("catalog_content_missing")
        return InspectContentUpdateOutcomeDTO(details.translations, tuple(issues))

    async def send(
        self, request: SendContentUpdateInputDTO
    ) -> SendContentUpdateOutcomeDTO:
        """Повторно читает цель, запрещает stale запись и отправляет ровно два поля."""
        target = request.inspection.target
        if (
            target.resource_type != "product"
            or not target.external_id.isdecimal()
            or int(target.external_id) <= 0
        ):
            raise PluginCallError("content_update_target_unsupported")
        inspection = await self.inspect(request.inspection)
        if inspection.issues:
            raise PluginCallError(inspection.issues[0])
        locales = tuple(text.locale for text in request.inspection.desired)
        if (
            content_texts(inspection.observed, locales).digest()
            != request.expected_observed_hash
        ):
            raise PluginCallError("external_content_changed")
        text = request.inspection.desired[0]
        response = await self.http.put(
            "/wp-json/wc/v3/products/" + target.external_id,
            payload={"name": text.title, "description": text.body},
            headers=await authorization(self.credentials),
        )
        if (
            not isinstance(response.body, dict)
            or str(response.body.get("id")) != target.external_id
        ):
            raise PluginCallError("invalid_publication_identity")
        return SendContentUpdateOutcomeDTO(True)
