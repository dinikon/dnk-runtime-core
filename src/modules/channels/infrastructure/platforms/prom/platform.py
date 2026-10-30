from uuid import UUID
from src.modules.channels.application.content_delivery.contracts import (
    PreparedContentRequest,
    ContentDeliveryResult,
    ContentReconciliationResult,
)
from src.modules.channels.application.content_media.contracts import PreparedGallery
from src.modules.channels.domain.content_delivery.value_object import DeliveryContextVO
from src.modules.channels.domain.content_delivery.error import ContentDeliveryError
from src.modules.channels.domain.product_representation.value_object import (
    LocalizedContent,
    PreparedPublicationContent,
    RepresentationIssue,
)
import hashlib
from src.modules.channels.domain.stock_sync.state import DesiredStockVO, StockFeaturesVO
from src.modules.channels.infrastructure.platforms.prom.stock import PromStock
from src.modules.channels.application.stock_sync.contracts import PlatformStockSnapshot
from src.modules.channels.infrastructure.platforms.prom.details import PromDetailsReader
from src.modules.channels.application.external_publication.catalog_details import (
    PublicationLookup,
    PublicationDetails,
)
import json
from urllib.parse import urlencode

from pydantic import ValidationError

from src.modules.channels.application.sync_run.port.source import (
    PublicationCheckpoint,
    PublicationObservation,
    PublicationPage,
)
from src.modules.channels.domain.external_publication.value_object import (
    PublicationKind,
)
from src.modules.channels.infrastructure.platforms.prom.publications import (
    PromPublicationReader,
)
from src.modules.channels.application.error import ChannelInputError
from src.modules.channels.application.error import VerificationFailure
from src.modules.channels.application.port.platform import (
    PlatformManifest,
    ValidatedConnection,
)
from src.modules.channels.domain.types import JsonObject
from src.modules.channels.domain.channel.value_object.connection_config import (
    ConnectionConfigVO,
)
from src.modules.channels.domain.channel.value_object.resource_identity import (
    ResourceIdentityVO,
)
from src.modules.channels.infrastructure.http import JsonHttp
from src.modules.channels.infrastructure.platforms.prom.models import (
    PromConfig,
    PromCredentials,
    PromGroups,
)


class PromPlatform:
    """Проверяет Prom по согласованному кандидату identity корневой группы."""

    def __init__(self, http: JsonHttp) -> None:
        """Собирает явную декларацию и HTTP-порт Prom."""
        self.http = http
        self.manifest = PlatformManifest(
            kind="prom",
            title="Prom",
            config_version=1,
            config_schema=PromConfig.model_json_schema(),
            credentials_schema=PromCredentials.model_json_schema(),
            supported_capabilities=(
                "verify_connection",
                "publications",
                "read_stock",
                "write_stock",
                "content_feed",
                "apply_content_feed",
            ),
            publication_parent_kind=PublicationKind.SIMPLE,
            stock_features=StockFeaturesVO(
                False, ("in_stock", "out_of_stock", "on_order"), ("no", "notify", "yes")
            ),
        )

    def media_metadata_fingerprint(self, alt: str) -> str:
        """Разделяет внешние attachment по alt; XML использует только исходный файл."""
        return hashlib.sha256(b"").hexdigest()

    def decode_config(self, config: ConnectionConfigVO) -> PromConfig:
        """Восстанавливает конкретную модель настроек Prom."""
        return PromConfig.model_validate(
            {
                "version": config.version,
                "endpoint": config.endpoint,
                "settings": config.settings,
            }
        )

    def validate(
        self, config: ConnectionConfigVO, credentials: JsonObject | None
    ) -> ValidatedConnection:
        """Проверяет настройки и явно сериализует полный комплект credentials."""
        try:
            typed = self.decode_config(config)
        except ValidationError as error:
            path = error.errors(include_input=False)[0]["loc"]
            location = (
                str(path[0])
                if path and path[0] in {"version", "endpoint", "settings"}
                else ""
            )
            raise ChannelInputError(
                "configuration_invalid",
                field="config" + ("." + location if location else ""),
            ) from None
        encoded = None
        if credentials is not None:
            try:
                secret = PromCredentials.model_validate(credentials)
            except ValidationError as error:
                path = error.errors(include_input=False)[0]["loc"]
                location = str(path[0]) if path and path[0] in {"token"} else ""
                raise ChannelInputError(
                    "credentials_invalid",
                    field="credentials" + ("." + location if location else ""),
                ) from None
            encoded = json.dumps(
                {"token": secret.token.get_secret_value()},
                ensure_ascii=False,
                separators=(",", ":"),
            ).encode("utf-8")
        return ValidatedConnection(
            config=ConnectionConfigVO.create(
                version=typed.version,
                endpoint=typed.endpoint,
                settings=typed.settings.model_dump(mode="json", exclude={"stock_sync"}),
            ),
            credentials=encoded,
            allow_stock_export=typed.settings.stock_sync.allow_export,
            currency=typed.settings.currency,
            locales=typed.settings.locales,
        )

    async def verify(
        self, config: ConnectionConfigVO, credentials: bytes
    ) -> ResourceIdentityVO:
        """Обходит страницы групп; неоднозначность и неполный обход отклоняются."""
        settings = self.decode_config(config)
        secret = PromCredentials.model_validate_json(credentials)
        seen: set[int] = set()
        roots: set[int] = set()
        last_id = None
        for _ in range(50):
            query = {"limit": 100}
            if last_id is not None:
                query["last_id"] = last_id
            data = await self.http.request(
                "GET",
                settings.endpoint + "/api/v1/groups/list?" + urlencode(query),
                headers={"Authorization": "Bearer " + secret.token.get_secret_value()},
            )
            page = PromGroups.model_validate(data)
            ids = [group.id for group in page.groups]
            if set(ids) & seen or len(ids) != len(set(ids)):
                raise VerificationFailure("resource_identity_unavailable")
            seen.update(ids)
            roots.update(
                group.id
                for group in page.groups
                if group.id > 0 and group.parent_group_id is None
            )
            if len(roots) > 1:
                raise VerificationFailure("resource_identity_unavailable")
            if len(ids) < 100:
                if len(roots) == 1:
                    return ResourceIdentityVO(
                        namespace="prom.root_group", key=str(next(iter(roots)))
                    )
                raise VerificationFailure("resource_identity_unavailable")
            last_id = ids[-1]
        raise VerificationFailure("resource_identity_unavailable")

    async def read_publications(
        self,
        *,
        config: ConnectionConfigVO,
        credentials: bytes,
        checkpoint: PublicationCheckpoint,
        parent_external_id: str | None = None,
    ) -> PublicationPage:
        """Восстанавливает конкретные настройки и читает один шаг источника."""
        return await PromPublicationReader(self.http).read(
            config=self.decode_config(config),
            credentials=PromCredentials.model_validate_json(credentials),
            checkpoint=checkpoint,
        )

    async def read_publication_dependencies(
        self,
        *,
        config: ConnectionConfigVO,
        credentials: bytes,
        keys: tuple[tuple[str, str], ...],
    ) -> tuple[PublicationObservation, ...]:
        """Дозагружает подтверждённые зависимости изменения структуры."""
        return await PromPublicationReader(self.http).read_dependencies(
            config=self.decode_config(config),
            credentials=PromCredentials.model_validate_json(credentials),
            keys=keys,
        )

    async def get_details(
        self,
        *,
        config: ConnectionConfigVO,
        credentials: bytes,
        publications: tuple[PublicationLookup, ...],
    ) -> PublicationDetails:
        """Восстанавливает конкретные типы пакета и читает полное семейство."""
        return await PromDetailsReader(self.http).read(
            config=self.decode_config(config),
            credentials=PromCredentials.model_validate_json(credentials),
            publications=publications,
        )

    def stock_target_key(self, native: JsonObject) -> str | None:
        """Нормализует нативный ключ без раскрытия модели платформы."""
        return None

    async def get_stock(
        self,
        *,
        config: ConnectionConfigVO,
        credentials: bytes,
        publication: PublicationLookup,
        parent: PublicationLookup | None = None,
    ) -> PlatformStockSnapshot:
        """Читает только остаток через конкретные типы пакета."""
        return await PromStock(self.http).get(
            config=self.decode_config(config),
            credentials=PromCredentials.model_validate_json(credentials),
            publication=publication,
            parent=parent,
        )

    async def set_stock(
        self,
        *,
        config: ConnectionConfigVO,
        credentials: bytes,
        publication: PublicationLookup,
        desired: DesiredStockVO,
    ) -> PlatformStockSnapshot:
        """Устанавливает абсолютное количество и проверяет результат чтением."""
        return await PromStock(self.http).set(
            config=self.decode_config(config),
            credentials=PromCredentials.model_validate_json(credentials),
            publication=publication,
            desired=desired,
        )

    def content_issues(
        self, targets: tuple[PreparedPublicationContent, ...]
    ) -> tuple[RepresentationIssue, ...]:
        """Этот пакет пока не предоставляет исходящую API-доставку контента."""
        return (RepresentationIssue("content_platform_unsupported"),)

    def prepare_content(
        self,
        *,
        context: DeliveryContextVO,
        content: LocalizedContent,
        gallery: PreparedGallery | None,
        reserved_media_ids: tuple[UUID, ...],
    ) -> PreparedContentRequest:
        """Отклоняет неподдерживаемую запись до любых сетевых операций."""
        raise ContentDeliveryError("content_platform_unsupported")

    async def send_content(
        self,
        *,
        config: ConnectionConfigVO,
        credentials: bytes,
        request: PreparedContentRequest,
    ) -> ContentDeliveryResult:
        """Не отправляет неподдерживаемые запросы."""
        raise ContentDeliveryError("content_platform_unsupported")

    async def reconcile_content(
        self,
        *,
        config: ConnectionConfigVO,
        credentials: bytes,
        request: PreparedContentRequest,
    ) -> ContentReconciliationResult:
        """Не выполняет сверку чужого формата платформы."""
        raise ContentDeliveryError("content_platform_unsupported")
