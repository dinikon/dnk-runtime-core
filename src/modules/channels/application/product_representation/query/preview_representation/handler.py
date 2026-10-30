from src.modules.channels.application.channel.port.query_repository import (
    ChannelQueryRepository,
)
from src.modules.channels.application.error import ChannelInputError
from src.modules.channels.application.port.platform import PlatformRegistry
from src.modules.channels.application.product_representation.port.query_repository import (
    RepresentationQueryRepositoryProtocol,
)
from src.modules.channels.application.product_representation.query.preview_representation.dto import (
    PreviewRepresentationResultDTO,
)
from src.modules.channels.application.product_representation.query.preview_representation.query import (
    PreviewRepresentationQuery,
)
from src.modules.channels.application.product_representation.service.builder import (
    RepresentationBuilder,
)
from src.modules.channels.domain.catalog_binding.error import CatalogBindingError
from src.modules.channels.domain.channel.error import ChannelNotFoundError
from src.modules.channels.domain.channel.value_object.connection_config import (
    ConnectionConfigVO,
)
from src.modules.shared.domain.time.clock_port import ClockPort


class PreviewRepresentationHandler:
    """Читает публичные настройки и группу, затем вызывает единый builder."""

    def __init__(
        self,
        *,
        channels: ChannelQueryRepository,
        representations: RepresentationQueryRepositoryProtocol,
        platforms: PlatformRegistry,
        builder: RepresentationBuilder,
        clock: ClockPort,
    ) -> None:
        """Получает только порты и сервис; credentials и UoW ему не нужны."""
        self._channels = channels
        self._representations = representations
        self._platforms = platforms
        self._builder = builder
        self._clock = clock

    async def execute(
        self, query: PreviewRepresentationQuery
    ) -> PreviewRepresentationResultDTO:
        """Проверяет запрошенные локали по типизированным настройкам пакета платформы."""
        channel = await self._channels.get(query.channel_id)
        if channel is None:
            raise ChannelNotFoundError()
        binding = await self._representations.binding(
            channel_id=query.channel_id, group_id=query.group_id
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
        locales = query.locales if query.locales is not None else connection.locales
        if (
            not locales
            or len(set(locales)) != len(locales)
            or any(locale not in connection.locales for locale in locales)
        ):
            raise ChannelInputError("representation_locales_invalid", field="locales")
        return PreviewRepresentationResultDTO(
            representation=await self._builder.build(
                channel_id=query.channel_id,
                binding=binding,
                platform=channel.platform_kind,
                config_revision=channel.config_revision,
                locales=locales,
                as_of=self._clock.now(),
            )
        )
