from src.modules.channels.application.external_publication.identity_contract import (
    PublicationIdentityPolicyDTO,
)
from dataclasses import asdict, dataclass, field
from datetime import datetime
from decimal import Decimal
from src.modules.channels.domain.external_publication.value_object.core import JsonValue

from src.modules.channels.domain.external_publication.value_object.payload import (
    PublicationPayloadVO,
)
from src.modules.channels.domain.external_publication.value_object.meta import (
    PublicationMetaVO,
)

type ProviderJsonValue = str | int | float | Decimal | bool | None | list[
    ProviderJsonValue
] | dict[str, ProviderJsonValue]


@dataclass(frozen=True, slots=True)
class ResourceSettingsDTO:
    """Передаёт immutable параметры текущего внешнего ресурса."""

    endpoint: str
    options: dict[str, JsonValue]


@dataclass(frozen=True, slots=True)
class ConnectionCredentialsDTO:
    """Хранит секреты только на время текущего сетевого шага."""

    values: dict[str, str] = field(repr=False)


@dataclass(frozen=True, slots=True)
class VerifyConnectionInputDTO:
    """Ограничивает проверку одним подключением."""

    settings: ResourceSettingsDTO


@dataclass(frozen=True, slots=True)
class VerifyConnectionOutcomeDTO:
    """Возвращает подтверждённую identity либо безопасную причину отказа."""

    identity: str | None
    reason_code: str | None = None
    limitations: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class PublicationCoreDTO:
    """Описывает нормализованный core результата read-плагина."""

    resource_type: str
    external_id: str
    external_sku: str | None
    price: Decimal | None
    sale_price: Decimal | None
    currency: str | None
    quantity: Decimal | None
    stock_status: str
    title: str | None
    title_locale: str | None
    main_image_url: str | None
    source_updated_at: datetime | None
    warnings: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ObservedPublicationDTO:
    """Передаёт одну проверенную проекцию платформы без ORM и токенов."""

    resource_type: str
    external_id: str
    payload: PublicationPayloadVO
    meta: PublicationMetaVO
    source_updated_at: datetime | None

    @property
    def core(self) -> PublicationCoreDTO:
        """Возвращает временную типизированную проекцию для details/Draft."""
        return PublicationCoreDTO(
            **asdict(
                self.payload.to_core(
                    self.resource_type,
                    self.external_id,
                    self.source_updated_at,
                    self.meta.read_issues,
                )
            )
        )


@dataclass(frozen=True, slots=True)
class ReadPublicationPageInputDTO:
    """Фиксирует ресурс и versioned checkpoint одного bounded шага."""

    settings: ResourceSettingsDTO
    resource_identity: str
    checkpoint: dict[str, JsonValue]


@dataclass(frozen=True, slots=True)
class ReadPublicationPageOutcomeDTO:
    """Возвращает порцию, checkpoint и явное завершение обхода."""

    publications: tuple[ObservedPublicationDTO, ...]
    checkpoint: dict[str, JsonValue]
    complete: bool
    invalid: int = 0


@dataclass(frozen=True, slots=True)
class ReadPublicationDetailsInputDTO:
    """Адресует одну публикацию проверенного ресурса для полного чтения."""

    settings: ResourceSettingsDTO
    resource_identity: str
    resource_type: str
    external_id: str
    provider_context: dict[str, JsonValue] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class PublicationTranslationDTO:
    """Передаёт реально прочитанный текст одной настроенной локали."""

    locale: str
    title: str | None
    body: str | None


@dataclass(frozen=True, slots=True)
class PublicationImageDTO:
    """Описывает изображение источника без файлового ID нашей платформы."""

    id: str
    url: str
    alt: str = ""


@dataclass(frozen=True, slots=True)
class ReadPublicationDetailsOutcomeDTO:
    """Возвращает содержимое для явного импорта, отдельно от списка публикаций."""

    core: PublicationCoreDTO
    translations: tuple[PublicationTranslationDTO, ...]
    images: tuple[PublicationImageDTO, ...]
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ConnectionSettingsReferencesDTO:
    """Передаёт используемые настройками коды для проверки через владельца справочников."""

    locales: tuple[str, ...] = ()
    currencies: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class PluginManifestDTO:
    """Описывает реализованные возможности и форму конфигурации плагина."""

    kind: str
    label: str
    sdk_version: int
    config_version: int
    capabilities: tuple[str, ...]
    credentials_schema: dict[str, JsonValue]
    endpoint_schema: dict[str, JsonValue]
    settings_schema: dict[str, JsonValue]
    publication_identity: PublicationIdentityPolicyDTO | None = None


@dataclass(frozen=True, slots=True)
class HttpResultDTO:
    """Передаёт JSON и безопасные заголовки без конкретного HTTP клиента."""

    body: ProviderJsonValue
    headers: dict[str, str]
