from src.modules.channels.application.product_representation.contracts import (
    PreparedRepresentation,
)
from src.modules.channels.domain.product_representation.value_object import (
    RepresentationIssue,
)
from dataclasses import dataclass
from uuid import UUID

from src.modules.channels.application.channel.port.query_repository import (
    ChannelQueryRepository,
    ChannelReadRow,
)
from src.modules.channels.application.port.platform import PlatformRegistry
from src.modules.channels.application.product_representation.contracts import (
    RepresentationBindingSource,
    RepresentationState,
)
from src.modules.channels.application.product_representation.port.query_repository import (
    RepresentationQueryRepositoryProtocol,
)
from src.modules.channels.domain.channel.error import ChannelNotFoundError
from src.modules.channels.domain.catalog_binding.error import CatalogBindingError
from src.modules.channels.domain.channel.value_object.connection_config import (
    ConnectionConfigVO,
)
from src.modules.channels.domain.product_representation.error import (
    ProductRepresentationError,
)


@dataclass(frozen=True, slots=True)
class RepresentationContext:
    """Публичный контекст группы, конфигурации и сохранённого намерения."""

    channel: ChannelReadRow
    binding: RepresentationBindingSource
    state: RepresentationState
    locales: tuple[str, ...]


class RepresentationReader:
    """Общая read-координация редактора и команд без восстановления агрегатов."""

    def __init__(
        self,
        *,
        channels: ChannelQueryRepository,
        representations: RepresentationQueryRepositoryProtocol,
        platforms: PlatformRegistry,
    ) -> None:
        """Получает порты одного внешнего UoW."""
        self._channels = channels
        self._representations = representations
        self._platforms = platforms

    async def load(self, *, channel_id: UUID, group_id: UUID) -> RepresentationContext:
        """Проверяет принадлежность до чтения overrides и нормализует настройки пакетом."""
        channel = await self._channels.get(channel_id)
        if channel is None:
            raise ChannelNotFoundError()
        binding = await self._representations.binding(
            channel_id=channel_id, group_id=group_id
        )
        if binding is None:
            raise CatalogBindingError("binding_not_found")
        connection = self._platforms.get(channel.platform_kind).validate(
            ConnectionConfigVO.create(
                version=channel.config.version,
                endpoint=channel.config.endpoint,
                settings=channel.config.settings,
            ),
            None,
        )
        return RepresentationContext(
            channel,
            binding,
            await self._representations.state(group_id),
            connection.locales,
        )

    def content_issues(
        self, representation: "PreparedRepresentation"
    ) -> tuple["RepresentationIssue", ...]:
        """Получает ограничения исходящей доставки из установленного пакета."""
        return self._platforms.get(representation.platform).content_issues(
            representation.preparation.targets
        )

    @staticmethod
    def require_context(
        context: RepresentationContext,
        *,
        expected_revision: int,
        expected_binding_revision: int,
        expected_config_revision: int,
    ) -> None:
        """Отклоняет устаревший редактор до валидации и записи его документа."""
        if expected_revision != context.state.revision:
            raise ProductRepresentationError(
                "representation_revision_conflict", conflict=True
            )
        if expected_binding_revision != context.binding.revision:
            raise ProductRepresentationError(
                "representation_binding_changed", conflict=True
            )
        if expected_config_revision != context.channel.config_revision:
            raise ProductRepresentationError(
                "representation_config_changed", conflict=True
            )
