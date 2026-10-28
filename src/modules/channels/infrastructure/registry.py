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


class InstalledPlatforms:
    """Неизменяемый реестр платформ, собираемый на внешней границе приложения."""

    def __init__(self, http: JsonHttp | None = None) -> None:
        """Устанавливает три пакета с общим безопасным транспортом."""
        client = http or SafeJsonHttp()
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
