"""Сборка безопасной проекции публикаций Console."""

from src.modules.channels.application.catalog_binding.publication_views import (
    BindingPublicationViews,
)
from src.modules.shared.domain.time.clock_port import ClockPort


from src.modules.channels.application.external_publication.query.get_publication.query import (
    GetPublicationQuery,
)
from src.modules.channels.application.external_publication.query.get_publication.dto import (
    GetPublicationResultDTO,
)
from src.modules.channels.application.external_publication.port.query_repository import (
    PublicationQueryRepository,
)
from src.modules.channels.application.external_publication.representation import (
    build_card,
)
from src.modules.channels.application.port.platform import PlatformRegistry
from src.modules.channels.application.error import ChannelInputError
from src.modules.channels.domain.channel.error import ChannelNotFoundError
from src.modules.channels.domain.external_publication.error import (
    ExternalPublicationNotFoundError,
)


class GetPublicationHandler:
    """Читает локальные данные; не вызывает API источника."""

    def __init__(
        self,
        repository: PublicationQueryRepository,
        platforms: PlatformRegistry,
        bindings: BindingPublicationViews,
        clock: ClockPort,
    ) -> None:
        """Принимает read-side и установленный каталог настроек."""
        self.repository, self.platforms = repository, platforms
        self.bindings, self.clock = bindings, clock

    async def execute(self, query: GetPublicationQuery) -> GetPublicationResultDTO:
        """Собирает карточки с явно выбранным языком."""
        connection = await self.repository.connection(query.channel_id)
        if connection is None:
            raise ChannelNotFoundError("Канал не найден.")
        settings = self.platforms.get(connection.platform_kind).validate(
            connection.config, None
        )
        locale = query.locale or settings.locales[0]
        if locale not in settings.locales:
            raise ChannelInputError("locale_invalid", field="locale")
        selected = await self.repository.get(connection.id, query.publication_id)
        if selected is None:
            raise ExternalPublicationNotFoundError("Публикация не найдена.")
        root = (
            await self.repository.get(connection.id, selected.parent_id)
            if selected.parent_id
            else selected
        )
        if root is None:
            raise ExternalPublicationNotFoundError("Основная публикация не найдена.")
        children = await self.repository.children(connection.id, (root.id,))
        summaries = await self.bindings.summaries(
            connection.id, (root.id,), locale, self.clock.now()
        )
        card = build_card(
            root=root,
            children=children,
            locale=locale,
            config_revision=connection.config_revision,
            selected_id=selected.id,
            bindings=summaries.get(root.id, ()),
        )
        return GetPublicationResultDTO(card, locale, settings.locales)
