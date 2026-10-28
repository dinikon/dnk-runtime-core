"""Сборка безопасной проекции публикаций Console."""

from src.modules.channels.application.catalog_binding.publication_views import (
    BindingPublicationViews,
)
from src.modules.shared.domain.time.clock_port import ClockPort


from src.modules.channels.application.external_publication.query.list_publications.query import (
    ListPublicationsQuery,
)
from src.modules.channels.application.external_publication.query.list_publications.dto import (
    ListPublicationsResultDTO,
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


class ListPublicationsHandler:
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

    async def execute(self, query: ListPublicationsQuery) -> ListPublicationsResultDTO:
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
        if query.offset < 0 or not 1 <= query.limit <= 100:
            raise ChannelInputError("pagination_invalid")
        if query.binding not in ("", "linked", "unlinked"):
            raise ChannelInputError("binding_filter_invalid", field="binding")
        roots, total = await self.repository.list_roots(
            connection.id, query.search, query.offset, query.limit, query.binding
        )
        children = await self.repository.children(
            connection.id, tuple(root.id for root in roots)
        )
        summaries = await self.bindings.summaries(
            connection.id, tuple(v.id for v in roots), locale, self.clock.now()
        )
        cards = tuple(
            build_card(
                root=root,
                children=tuple(item for item in children if item.parent_id == root.id),
                locale=locale,
                config_revision=connection.config_revision,
                bindings=summaries.get(root.id, ()),
            )
            for root in roots
        )
        return ListPublicationsResultDTO(
            cards, total, query.offset, query.limit, locale, settings.locales
        )
