from src.modules.channels.application.error import ChannelInputError
from src.modules.channels.application.port.platform import Platform, PlatformManifest
from src.modules.channels.infrastructure.http import JsonHttp, SafeJsonHttp
from src.modules.channels.infrastructure.platforms.prom.platform import PromPlatform
from src.modules.channels.infrastructure.platforms.rozetka.platform import (
    RozetkaPlatform,
)
from src.modules.channels.infrastructure.platforms.woocommerce.platform import (
    WooCommercePlatform,
)
from src.modules.channels.application.content_feed.port.serializer import (
    ContentFeedSerializerProtocol,
)
from src.modules.channels.application.content_feed.error import FeedBuildError
from src.modules.channels.infrastructure.platforms.prom.feed_serializer import (
    PromYmlSerializer,
)
from src.modules.channels.infrastructure.platforms.prom.feed_import import (
    PromFeedImporter,
)
from src.modules.channels.application.content_feed.port.importer import FeedImporterPort


class InstalledPlatforms:
    """Неизменяемый реестр платформ, собираемый на внешней границе приложения."""

    def __init__(self, http: JsonHttp | None = None) -> None:
        """Устанавливает три пакета с общим безопасным транспортом."""
        client = http or SafeJsonHttp()
        self._feed_importer = PromFeedImporter(client)
        self._platforms: dict[str, Platform] = {
            p.manifest.kind: p
            for p in (
                PromPlatform(client),
                RozetkaPlatform(client),
                WooCommercePlatform(client),
            )
        }

    def get(self, kind: str) -> Platform:
        """Возвращает фасад либо безопасную ошибку неизвестной платформы."""
        try:
            return self._platforms[kind]
        except KeyError:
            raise ChannelInputError("platform_unknown", field="platform_kind") from None

    def manifests(self) -> tuple[PlatformManifest, ...]:
        """Возвращает декларации в стабильном порядке регистрации."""
        return tuple(p.manifest for p in self._platforms.values())

    def content_feed_serializer(self, kind: str) -> ContentFeedSerializerProtocol:
        """Связывает конкретный XML-пакет с его портом без импорта модели в ядро."""
        if (
            kind == "prom"
            and "content_feed" in self.get(kind).manifest.supported_capabilities
        ):
            return PromYmlSerializer()
        raise FeedBuildError("feed_platform_unsupported")

    def feed_importer(self, kind: str) -> FeedImporterPort:
        """Выдаёт конкретный адаптер импорта через общий порт."""
        if (
            kind == "prom"
            and "apply_content_feed" in self.get(kind).manifest.supported_capabilities
        ):
            return self._feed_importer
        raise FeedBuildError("feed_import_unsupported")
