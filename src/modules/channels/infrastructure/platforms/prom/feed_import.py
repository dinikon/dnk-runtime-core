from typing import Literal
from hashlib import sha256
from urllib.parse import urlencode, urlsplit
from uuid import UUID
import re
import unicodedata

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from src.modules.channels.application.content_feed.contracts import RenderedFeed
from src.modules.channels.application.content_feed.error import FeedBuildError
from src.modules.channels.application.content_feed.import_contracts import (
    FeedSubmissionResult,
    FeedPollResult,
)
from src.modules.channels.application.error import VerificationFailure
from src.modules.channels.domain.channel.value_object.connection_config import (
    ConnectionConfigVO,
)
from src.modules.channels.domain.content_feed.delivery import (
    FeedImportReportVO,
    FeedImportIssueVO,
    FeedFieldVerificationVO,
    FeedPublicationVerificationVO,
)
from src.modules.channels.infrastructure.http import JsonHttp
from src.modules.channels.infrastructure.platforms.base import StrictModel
from src.modules.channels.infrastructure.platforms.prom.models import (
    PromConfig,
    PromCredentials,
)
from src.modules.channels.infrastructure.platforms.prom.details import (
    PromProductDetails,
)
from src.modules.channels.infrastructure.platforms.prom.publications import (
    PromProductResponse,
)
from src.modules.channels.infrastructure.platforms.prom.feed_serializer import (
    PromYmlSerializer,
)
from src.modules.channels.infrastructure.product_representation.rich_text import (
    RepresentationRichTextSanitizer,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


class PromImportRequest(StrictModel):
    """Фиксированный allowlist; URL с токеном сериализуется только в шифруемый документ."""

    url: str = Field(min_length=1, max_length=1024, repr=False)
    force_update: bool = False
    only_available: Literal[False] = False
    only_update: Literal[False] = False
    mark_missing_product_as: Literal["none"] = "none"
    updated_fields: tuple[
        Literal["name", "description", "name_ua", "description_ua", "images_urls"], ...
    ] = ("name", "description", "name_ua", "description_ua", "images_urls")


class PromExpectedOffer(StrictModel):
    """Снимок выбранных полей одной существующей позиции, а не копия XML."""

    publication_id: UUID
    native_id: str
    import_key: str
    name: str | None
    description: str | None
    name_ua: str | None
    description_ua: str | None
    pictures: tuple[str, ...] = Field(repr=False)


class PromImportDocument(StrictModel):
    """Конкретная версия подготовленного запроса для восстановления worker."""

    version: Literal[1] = 1
    request: PromImportRequest
    expected: tuple[PromExpectedOffer, ...]
    xml_hash: str
    offers_count: int


class PromImportProduct(PromProductDetails):
    """Добавляет базовое описание к существующей модели чтения Prom."""

    description: str | None = None


class PromImportProductPage(BaseModel):
    """Отсутствующий products не считается пустой страницей."""

    products: list[PromImportProduct]


class PromImportAcceptance(BaseModel):
    """Документированное принятие параметров не является итогом импорта."""

    model_config = ConfigDict(strict=True)
    status: Literal["success", "error"]
    id: str | int | None = None


class PromImportReport(BaseModel):
    """Неизвестный status допускается только как ещё не распознанный отчёт."""

    model_config = ConfigDict(strict=True)
    status: str
    total: int | None = Field(default=None, ge=0)
    updated: int | None = Field(default=None, ge=0)
    created: int | None = Field(default=None, ge=0)
    imported: int | None = Field(default=None, ge=0)
    not_changed: int | None = Field(default=None, ge=0)
    not_in_fle: int | None = Field(default=None, ge=0)
    with_errors_count: int | None = Field(default=None, ge=0)
    errors: list[dict[str, object]] = Field(default_factory=list)


class PromFeedImporter:
    """Подготавливает полный XML-импорт и различает принятие, отчёт и наблюдаемые поля."""

    def __init__(self, http: JsonHttp) -> None:
        """Переиспользует transport пакета без автоматического повторения POST."""
        self.http = http
        self.rich_text = RepresentationRichTextSanitizer()

    @staticmethod
    def _config(config: ConnectionConfigVO) -> PromConfig:
        """Восстанавливает конкретные настройки внутри пакета."""
        return PromConfig.model_validate(
            {
                "version": config.version,
                "endpoint": config.endpoint,
                "settings": config.settings,
            }
        )

    @staticmethod
    def _headers(credentials: bytes) -> dict[str, str]:
        """Использует настоящее значение SecretStr; базовые поля запрашиваются на ru."""
        secret = PromCredentials.model_validate_json(credentials)
        return {
            "Authorization": "Bearer " + secret.token.get_secret_value(),
            "X-LANGUAGE": "ru",
        }

    async def prepare(
        self,
        *,
        config: ConnectionConfigVO,
        credentials: bytes,
        document: RenderedFeed,
        feed_url: str,
        force_update: bool,
    ) -> bytes:
        """Проверяет все offer и несопоставленные поля свежим чтением Prom до POST."""
        if document.snapshot is None:
            raise FeedBuildError("feed_import_snapshot_missing")
        targets = {
            t.publication_id.uuid: t
            for group in document.snapshot.groups
            for t in group.targets
        }
        if not targets:
            raise FeedBuildError("feed_import_no_targets")
        request = PromImportRequest(url=feed_url, force_update=force_update)
        products = await self._products(config=config, credentials=credentials)
        owners: dict[str, PromImportProduct] = {}
        duplicates: set[str] = set()
        for product in products:
            if product.external_id:
                if product.external_id in owners:
                    duplicates.add(product.external_id)
                owners[product.external_id] = product
        keys = {v.publication_id: v.import_key for v in document.snapshot.publications}
        target_keys: dict[str, UUID] = {}
        for identifier, target in targets.items():
            key = keys.get(identifier)
            if key is None or key in target_keys or key in duplicates:
                raise FeedBuildError(
                    "feed_import_key_duplicate", publication_id=identifier
                )
            if key not in owners or str(owners[key].id) != target.external_id:
                raise FeedBuildError(
                    "feed_import_identity_changed", publication_id=identifier
                )
            target_keys[key] = identifier
        root = PromYmlSerializer._parse(document.content)
        offers, _ = PromYmlSerializer._validate(root)
        expected = []
        for key, node in offers.items():
            if key not in owners:
                raise FeedBuildError("feed_import_would_create_product")
            if key in duplicates:
                raise FeedBuildError("feed_import_key_duplicate")
            native = owners[key]
            value = PromExpectedOffer(
                publication_id=target_keys.get(key, UUID(int=0)),
                native_id=str(native.id),
                import_key=key,
                name=node.findtext("name"),
                description=node.findtext("description"),
                name_ua=node.findtext("name_ua"),
                description_ua=node.findtext("description_ua"),
                pictures=tuple(n.text or "" for n in node.findall("picture")),
            )
            if key in target_keys:
                expected.append(value)
            elif not self._unchanged(value, native):
                raise FeedBuildError("feed_import_unmatched_content_changed")
        return (
            PromImportDocument(
                request=request,
                expected=tuple(expected),
                xml_hash=sha256(document.content).hexdigest(),
                offers_count=len(offers),
            )
            .model_dump_json()
            .encode()
        )

    async def _products(
        self, *, config: ConnectionConfigVO, credentials: bytes
    ) -> tuple[PromImportProduct, ...]:
        """Обходит полный список, обнаруживая неполный обход и повторяющиеся страницы."""
        endpoint = self._config(config).endpoint
        result: list[PromImportProduct] = []
        seen: set[int] = set()
        last = None
        for _ in range(1000):
            query = {"limit": 100}
            if last is not None:
                query["last_id"] = last
            page = PromImportProductPage.model_validate(
                await self.http.request(
                    "GET",
                    endpoint + "/api/v1/products/list?" + urlencode(query),
                    headers=self._headers(credentials),
                )
            )
            if any(product.id in seen for product in page.products) or len(
                {p.id for p in page.products}
            ) != len(page.products):
                raise FeedBuildError("feed_import_listing_incomplete")
            seen.update(product.id for product in page.products)
            result.extend(page.products)
            if len(page.products) < 100:
                return tuple(result)
            last = page.products[-1].id
        raise FeedBuildError("feed_import_listing_incomplete")

    async def submit(
        self, *, config: ConnectionConfigVO, credentials: bytes, payload: bytes
    ) -> FeedSubmissionResult:
        """Таймаут, 5xx, неизвестный ответ и отсутствие ID не приводят к повтору POST."""
        document = PromImportDocument.model_validate_json(payload)
        try:
            response = PromImportAcceptance.model_validate(
                await self.http.request(
                    "POST",
                    self._config(config).endpoint + "/api/v1/products/import_url",
                    headers=self._headers(credentials),
                    body=document.request.model_dump(mode="json"),
                )
            )
            if response.status == "error":
                return FeedSubmissionResult(
                    "rejected", error_code="feed_import_rejected"
                )
            identifier = str(response.id) if response.id is not None else ""
            if (
                not identifier.isascii()
                or not identifier.isdigit()
                or not 0 < int(identifier) <= 2**63 - 1
            ):
                return FeedSubmissionResult(
                    "unknown", error_code="feed_import_acceptance_unknown"
                )
            return FeedSubmissionResult("accepted", identifier)
        except VerificationFailure as error:
            rejected = error.code in {
                "invalid_credentials",
                "permission_missing",
                "endpoint_invalid",
            }
            return FeedSubmissionResult(
                "rejected" if rejected else "unknown",
                error_code=(
                    "feed_import_rejected"
                    if rejected
                    else "feed_import_acceptance_unknown"
                ),
            )
        except (ValidationError, ValueError, TypeError):
            return FeedSubmissionResult(
                "unknown", error_code="feed_import_acceptance_unknown"
            )

    async def poll(
        self, *, config: ConnectionConfigVO, credentials: bytes, external_id: str
    ) -> FeedPollResult:
        """Распознаёт только опубликованные финальные статусы; остальные ожидаются ограниченно."""
        if (
            not external_id.isascii()
            or not external_id.isdigit()
            or not 0 < int(external_id) <= 2**63 - 1
        ):
            raise FeedBuildError("feed_import_id_invalid")
        try:
            raw = await self.http.request(
                "GET",
                self._config(config).endpoint
                + "/api/v1/products/import/status/"
                + external_id,
                headers=self._headers(credentials),
            )
            report = PromImportReport.model_validate(raw)
            if report.status not in {"SUCCESS", "PARTIAL", "FATAL"}:
                return FeedPollResult(error_code="feed_import_report_pending")
            stages = (
                "download",
                "store_file",
                "validation",
                "import",
                "download_images",
            )
            issues = tuple(
                FeedImportIssueVO("feed_import_provider_error", stage)
                for stage in stages
                if any(error.get(stage) for error in report.errors[:100])
            )
            if report.errors and not issues:
                issues = (FeedImportIssueVO("feed_import_provider_error", "unknown"),)
            return FeedPollResult(
                FeedImportReportVO(
                    report.status,
                    report.total,
                    report.updated,
                    report.created,
                    report.imported,
                    report.not_changed,
                    report.not_in_fle,
                    report.with_errors_count,
                    issues,
                )
            )
        except VerificationFailure as error:
            blocked = error.code in {"invalid_credentials", "permission_missing"}
            return FeedPollResult(
                error_code=(
                    "feed_import_access_denied"
                    if blocked
                    else "feed_import_report_unavailable"
                ),
                blocked=blocked,
            )
        except (ValidationError, ValueError, TypeError):
            return FeedPollResult(error_code="feed_import_report_unrecognized")

    async def verify(
        self, *, config: ConnectionConfigVO, credentials: bytes, payload: bytes
    ) -> tuple[FeedPublicationVerificationVO, ...]:
        """Проверяет поля независимо; совпадение количества фото не доказывает их содержимое."""
        document = PromImportDocument.model_validate_json(payload)
        result = []
        for value in document.expected:
            raw = await self.http.request(
                "GET",
                self._config(config).endpoint + "/api/v1/products/" + value.native_id,
                headers=self._headers(credentials),
            )
            native = PromImportProduct.model_validate(
                PromProductResponse.model_validate(raw).product
            )
            if (
                str(native.id) != value.native_id
                or native.external_id != value.import_key
            ):
                raise FeedBuildError("feed_import_identity_changed")
            fields = []
            for field, locale, expected, observed in self._text_fields(value, native):
                normal = self._body if field == "body" else self._title
                fields.append(
                    FeedFieldVerificationVO(
                        field,
                        locale,
                        (
                            "confirmed"
                            if normal(expected) == normal(observed)
                            else "mismatch"
                        ),
                    )
                )
            observed = native.original_image_urls
            wanted = self._canonical_pictures(value.pictures)
            status = (
                "confirmed"
                if wanted == observed
                else "mismatch" if len(wanted) != len(observed) else "unconfirmed"
            )
            fields.append(FeedFieldVerificationVO("gallery", None, status))
            public_images = tuple(
                url
                for url in observed
                if urlsplit(url).scheme == "https"
                and urlsplit(url).hostname == "images.prom.ua"
                and not urlsplit(url).query
                and not urlsplit(url).username
                and not urlsplit(url).password
                and not urlsplit(url).fragment
            )
            result.append(
                FeedPublicationVerificationVO(
                    EntityIdVO(value.publication_id),
                    value.native_id,
                    value.import_key,
                    tuple(fields),
                    public_images,
                )
            )
        return tuple(result)

    def _unchanged(
        self, expected: PromExpectedOffer, native: PromImportProduct
    ) -> bool:
        """Блокирует перезапись несопоставленного контента устаревшим полным исходником."""
        for field, _, wanted, observed in self._text_fields(expected, native):
            normal = self._body if field == "body" else self._title
            if normal(wanted) != normal(observed):
                return False
        return self._canonical_pictures(expected.pictures) == native.original_image_urls

    @staticmethod
    def _text_fields(
        expected: PromExpectedOffer, native: PromImportProduct
    ) -> tuple[tuple[str, str, str | None, str | None], ...]:
        """Сохраняет независимость украинского и русского контента."""
        return (
            (
                "title",
                "ru",
                expected.name,
                native.name_multilang.get("ru", native.name),
            ),
            (
                "body",
                "ru",
                expected.description,
                native.description_multilang.get("ru", native.description),
            ),
            (
                "title",
                "uk",
                expected.name_ua,
                native.name_multilang.get("uk", native.name_multilang.get("ua")),
            ),
            (
                "body",
                "uk",
                expected.description_ua,
                native.description_multilang.get(
                    "uk", native.description_multilang.get("ua")
                ),
            ),
        )

    @staticmethod
    def _canonical_pictures(values: tuple[str, ...]) -> tuple[str, ...]:
        """Использует тот же оригинальный адрес CDN, что существующий Prom details reader."""
        return tuple(
            re.sub(
                r"^(https?://images\.prom\.ua/[0-9]+)_w[0-9]+_h[0-9]+_",
                r"\1_",
                url,
                count=1,
                flags=re.IGNORECASE,
            )
            for url in values
        )

    @staticmethod
    def _title(value: str | None) -> str:
        """Сравнивает Unicode без изменения регистра и внутренних пробелов."""
        return unicodedata.normalize("NFC", value or "").strip()

    def _body(self, value: str | None) -> str:
        """Применяет существующую очистку HTML с сохранением значимых пробелов."""
        return self.rich_text.clean(value or "").strip()
