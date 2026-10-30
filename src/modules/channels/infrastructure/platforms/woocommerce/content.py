import json
import base64
import re
import logging
from hashlib import sha256
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from src.modules.channels.application.content_delivery.contracts import (
    ContentDeliveryResult,
    ContentMediaResult,
    ContentWriteOutcome,
    PreparedContentRequest,
    ContentMediaChecksum,
)
from src.modules.channels.application.content_media.contracts import PreparedGallery
from src.modules.channels.application.error import VerificationFailure
from src.modules.channels.domain.content_delivery.error import ContentDeliveryError
from src.modules.channels.domain.content_delivery.value_object import (
    DeliveryContextVO,
    DeliveryFieldIssueVO,
)
from src.modules.channels.domain.product_representation.value_object import (
    ContentOrigin,
    LocalizedContent,
    PreparedPublicationContent,
    RepresentationIssue,
)
from src.modules.channels.infrastructure.http import JsonHttp
from src.modules.channels.infrastructure.platforms.woocommerce.media import (
    WooGalleryAdapter,
)
from src.modules.channels.infrastructure.platforms.woocommerce.models import (
    WooCommerceConfig,
    WooCommerceCredentials,
)

logger = logging.getLogger(__name__)


class WooContentImage(BaseModel):
    """Явная форма изображения для запроса; src не включается в repr."""

    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    id: int | None = Field(default=None, ge=0, strict=True)
    src: str | None = Field(default=None, repr=False)
    alt: str | None = None


class WooProductContentUpdate(BaseModel):
    """Единственные разрешённые поля записи товара и контейнера."""

    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    name: str | None = None
    description: str | None = None
    images: tuple[WooContentImage, ...] | None = None


class WooVariationContentUpdate(BaseModel):
    """Запись вариации не содержит имени, SKU и атрибутов."""

    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    description: str | None = None
    image: WooContentImage | None = None


class WooContentMediaReference(BaseModel):
    """Соответствие элемента запроса локальному media для проверки ответа."""

    media_id: UUID
    remote_id: int | None = None


class WooPreparedContent(BaseModel):
    """Конкретный сохраняемый запрос пакета, без произвольного URL и заголовков."""

    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    external_id: int = Field(gt=0, strict=True)
    parent_external_id: int | None = Field(default=None, gt=0, strict=True)
    kind: str
    product: WooProductContentUpdate | None = None
    variation: WooVariationContentUpdate | None = None
    media: tuple[WooContentMediaReference, ...]


class WooObservedImage(BaseModel):
    """Проверяемый фрагмент ответа изображения."""

    id: int = Field(gt=0, strict=True)
    alt: str = ""
    src: str | None = Field(default=None, repr=False)


class WooObservedProduct(BaseModel):
    """Узкое наблюдение контента; остальные поля не применяются локально."""

    id: int = Field(gt=0, strict=True)
    type: str
    name: str
    description: str
    images: tuple[WooObservedImage, ...]


class WooObservedVariation(BaseModel):
    """Проверяемый ответ вариации без реконструкции полного товара."""

    id: int = Field(gt=0, strict=True)
    parent_id: int = Field(gt=0, strict=True)
    type: str
    description: str
    image: WooObservedImage | None = None


def woo_description(value: str) -> str:
    """Учитывает абзац wpautop для текста и внешние переводы строк ответа.

    Не удаляет теги, атрибуты или внутренние пробелы: иные изменения площадки
    требуют сверки. Текст внутри pre остаётся неизменным.
    """
    value = value.strip()
    if not value or re.search(
        r"<(?:p|h[1-6]|ul|ol|li|blockquote|pre|div|table)\b", value, re.IGNORECASE
    ):
        return value
    return "\n".join(
        "<p>" + part.replace("\n", "<br />\n") + "</p>"
        for part in re.split(r"\n\s*\n", value.replace("\r\n", "\n"))
    )


def woo_content_issues(
    targets: tuple[PreparedPublicationContent, ...],
) -> tuple[RepresentationIssue, ...]:
    """Показывает ограничения поддерживаемого режима до запуска доставки."""
    issues: list[RepresentationIssue] = []
    for target in targets:
        if target.publication_kind not in {"simple", "variable", "variant"}:
            issues.append(
                RepresentationIssue("content_target_unsupported", target.publication_id)
            )
        for content in target.content:
            if (
                target.publication_kind == "variant"
                and content.origins.title.kind is ContentOrigin.ITEM_OVERRIDE
            ):
                issues.append(
                    RepresentationIssue(
                        "content_variation_title_unsupported",
                        target.publication_id,
                        "title",
                        content.locale,
                    )
                )
            if (
                target.publication_kind == "variant"
                and content.gallery is not None
                and len(content.gallery) > 1
            ):
                issues.append(
                    RepresentationIssue(
                        "media_variation_gallery_unsupported",
                        target.publication_id,
                        "gallery",
                        content.locale,
                    )
                )
            if any(image.caption for image in content.gallery or ()):
                issues.append(
                    RepresentationIssue(
                        "media_caption_unsupported",
                        target.publication_id,
                        "gallery",
                        content.locale,
                    )
                )
    return tuple(issues)


class WooContentAdapter:
    """Отправляет только контент; повтор неоднозначного PUT заменяется чтением."""

    SCHEMA = "woocommerce.content.v1"

    def __init__(self, http: JsonHttp) -> None:
        """Переиспользует безопасный HTTP transport и существующую подготовку галереи."""
        self._http = http

    def prepare(
        self,
        *,
        context: DeliveryContextVO,
        content: LocalizedContent,
        gallery: PreparedGallery | None,
        reserved_media_ids: tuple[UUID, ...],
    ) -> PreparedContentRequest:
        """Сериализует конкретную модель без добавления полей из входящего raw."""
        try:
            identifier = int(context.external_id)
            parent = (
                int(context.parent_external_id) if context.parent_external_id else None
            )
            images = (
                WooGalleryAdapter(self._http).payload(gallery, reserved_media_ids)
                if gallery is not None
                else {}
            )
            if context.publication_kind == "variant":
                product = None
                variation = WooVariationContentUpdate(
                    description=(
                        woo_description(content.body)
                        if content.body is not None
                        else None
                    ),
                    **images,
                )
                if parent is None:
                    raise ContentDeliveryError("content_target_invalid")
            else:
                if context.publication_kind not in {"simple", "variable"}:
                    raise ContentDeliveryError("content_target_unsupported")
                product = WooProductContentUpdate(
                    name=content.title,
                    description=(
                        woo_description(content.body)
                        if content.body is not None
                        else None
                    ),
                    **images,
                )
                variation = None
            value = WooPreparedContent(
                external_id=identifier,
                parent_external_id=parent,
                kind=context.publication_kind,
                product=product,
                variation=variation,
                media=(
                    tuple(
                        WooContentMediaReference(
                            media_id=image.media_id,
                            remote_id=(
                                int(image.remote_media_id)
                                if image.remote_media_id
                                else None
                            ),
                        )
                        for image in gallery.images
                    )
                    if gallery
                    else ()
                ),
            )
        except (ValueError, ValidationError):
            raise ContentDeliveryError("content_request_invalid") from None
        semantic = [
            context.external_id,
            context.parent_external_id,
            context.publication_kind,
            content.locale,
            content.title if product else None,
            content.body,
            (
                [
                    [str(image.file_id), image.alt, image.caption]
                    for image in gallery.images
                ]
                if gallery
                else ([] if gallery is not None else None)
            ),
        ]

        return PreparedContentRequest(
            self.SCHEMA,
            value.model_dump_json(exclude_none=True).encode(),
            sha256(
                json.dumps(semantic, ensure_ascii=False, separators=(",", ":")).encode()
            ).hexdigest(),
        )

    def decode(self, request: PreparedContentRequest) -> WooPreparedContent:
        """Проверяет версию и форму сохранённого запроса до сетевого доступа."""
        if request.schema != self.SCHEMA:
            raise ContentDeliveryError("content_request_schema_unsupported")
        try:
            value = WooPreparedContent.model_validate_json(request.payload)
        except ValidationError:
            raise ContentDeliveryError("content_request_invalid") from None
        if (
            value.kind == "variant"
            and (
                value.variation is None
                or value.product is not None
                or value.parent_external_id is None
            )
        ) or (
            value.kind != "variant"
            and (
                value.kind not in {"simple", "variable"}
                or value.product is None
                or value.variation is not None
            )
        ):
            raise ContentDeliveryError("content_request_invalid")
        return value

    async def execute(
        self,
        *,
        config: WooCommerceConfig,
        credentials: WooCommerceCredentials,
        request: PreparedContentRequest,
        reconcile: bool,
        known_media: tuple[ContentMediaResult, ...] = (),
        media_checksums: tuple[ContentMediaChecksum, ...] = (),
    ) -> ContentDeliveryResult:
        """GET до записи проверяет адресата; любой неясный исход PUT остаётся unknown."""
        value = self.decode(request)
        path = (
            f"/products/{value.parent_external_id}/variations/{value.external_id}"
            if value.kind == "variant"
            else f"/products/{value.external_id}"
        )
        url = config.endpoint + "/wp-json/wc/v3" + path + "?context=edit"
        basic = base64.b64encode(
            (
                credentials.consumer_key.get_secret_value()
                + ":"
                + credentials.consumer_secret.get_secret_value()
            ).encode()
        ).decode()
        headers = {"Authorization": "Basic " + basic}
        sent = reconcile
        try:
            observed = await self._http.request("GET", url, headers=headers)
            trusted = {v.media_id: int(v.remote_id) for v in known_media}
            if reconcile:
                trusted.update(
                    await self._recover_media(value, observed, media_checksums)
                )
            result = self._assess(
                value, observed, accept_new_media=False, known_media=trusted
            )
            if result.outcome is ContentWriteOutcome.CONFIRMED:
                return result
            if reconcile:
                return ContentDeliveryResult(
                    ContentWriteOutcome.UNKNOWN,
                    fields=result.fields,
                    media=result.media,
                    error_code=result.error_code,
                    issues=result.issues,
                )
            patch = value.variation if value.kind == "variant" else value.product
            assert patch is not None
            sent = True
            response = await self._http.request(
                "PUT",
                url,
                headers=headers,
                body=patch.model_dump(mode="json", exclude_none=True),
            )
            result = self._assess(value, response, accept_new_media=True)
            if result.issues:
                logger.info(
                    "WooCommerce content differs: product_id=%s fields=%s",
                    value.external_id,
                    ",".join(v.field for v in result.issues),
                    extra={
                        "event": "channels.content.fields_mismatch",
                        "publication_external_id": str(value.external_id),
                        "reason_code": result.error_code,
                        "confirmed_fields": result.fields,
                    },
                )
            return result
        except VerificationFailure as error:
            # Даже HTTP 4xx может следовать за частичной загрузкой media в WordPress.
            outcome = (
                ContentWriteOutcome.UNKNOWN if sent else ContentWriteOutcome.REJECTED
            )
            return ContentDeliveryResult(outcome, error_code=error.code)
        except (ValidationError, ValueError):
            return ContentDeliveryResult(
                ContentWriteOutcome.UNKNOWN if sent else ContentWriteOutcome.REJECTED,
                error_code="content_provider_response_invalid",
            )
        except ContentDeliveryError as error:
            return ContentDeliveryResult(
                ContentWriteOutcome.UNKNOWN if sent else ContentWriteOutcome.REJECTED,
                error_code=error.code,
            )

    def compare(
        self, desired: WooPreparedContent, response: object, *, accept_new_media: bool
    ) -> ContentDeliveryResult | None:
        """Возвращает только полное подтверждение; частные факты сохраняет assess."""
        result = self._assess(desired, response, accept_new_media=accept_new_media)
        return result if result.outcome is ContentWriteOutcome.CONFIRMED else None

    def _assess(
        self,
        desired: WooPreparedContent,
        response: object,
        *,
        accept_new_media: bool,
        known_media: dict[UUID, int] | None = None,
    ) -> ContentDeliveryResult:
        """Проверяет каждое поле независимо и сохраняет доказанные media при частичном отказе."""
        fields: list[str] = []
        issues: list[DeliveryFieldIssueVO] = []
        if desired.kind == "variant":
            observed = WooObservedVariation.model_validate(response)
            patch = desired.variation
            assert patch is not None
            if (
                observed.id != desired.external_id
                or observed.parent_id != desired.parent_external_id
                or observed.type != "variation"
            ):
                raise ContentDeliveryError("content_target_changed")
            if patch.description is not None:
                if woo_description(observed.description) != woo_description(
                    patch.description
                ):
                    issues.append(DeliveryFieldIssueVO("body", "content_body_mismatch"))
                else:
                    fields.append("body")
            images = (observed.image,) if observed.image else ()
            wanted = (patch.image,) if patch.image and patch.image.id != 0 else ()
            has_gallery = patch.image is not None
        else:
            observed_product = WooObservedProduct.model_validate(response)
            product = desired.product
            assert product is not None
            if (
                observed_product.id != desired.external_id
                or observed_product.type != desired.kind
            ):
                raise ContentDeliveryError("content_target_changed")
            if product.name is not None:
                if observed_product.name != product.name:
                    issues.append(
                        DeliveryFieldIssueVO("title", "content_title_mismatch")
                    )
                else:
                    fields.append("title")
            if product.description is not None:
                if woo_description(observed_product.description) != woo_description(
                    product.description
                ):
                    issues.append(DeliveryFieldIssueVO("body", "content_body_mismatch"))
                else:
                    fields.append("body")
            images, wanted, has_gallery = (
                observed_product.images,
                product.images or (),
                product.images is not None,
            )
        media: list[ContentMediaResult] = []
        if has_gallery:
            exact_count = len(images) == len(wanted) == len(desired.media)
            gallery_matches = exact_count
            used_ids: set[int] = set()
            for actual, expected, reference in zip(images, wanted, desired.media):
                remote_id = reference.remote_id or (known_media or {}).get(
                    reference.media_id
                )
                alt_matches = actual.alt == (expected.alt or "")
                proved = (
                    actual.id == remote_id
                    if remote_id is not None
                    else accept_new_media and exact_count and alt_matches
                )
                if proved and actual.id not in used_ids:
                    media.append(ContentMediaResult(reference.media_id, str(actual.id)))
                    used_ids.add(actual.id)
                else:
                    gallery_matches = False
                if not alt_matches:
                    gallery_matches = False
            if gallery_matches:
                fields.append("gallery")
            else:
                issues.append(
                    DeliveryFieldIssueVO("gallery", "content_media_unconfirmed")
                )
        return ContentDeliveryResult(
            ContentWriteOutcome.PARTIAL if issues else ContentWriteOutcome.CONFIRMED,
            tuple(fields),
            tuple(media),
            issues[0].code if issues else None,
            tuple(issues),
        )

    async def _recover_media(
        self,
        desired: WooPreparedContent,
        response: object,
        checksums: tuple[ContentMediaChecksum, ...],
    ) -> dict[UUID, int]:
        """Доказывает Files → attachment сравнением исходных bytes без повторной загрузки."""
        if not checksums:
            return {}
        if desired.kind == "variant":
            observed = WooObservedVariation.model_validate(response)
            if (
                observed.id != desired.external_id
                or observed.parent_id != desired.parent_external_id
                or observed.type != "variation"
            ):
                raise ContentDeliveryError("content_target_changed")
            images = (observed.image,) if observed.image else ()
        else:
            product = WooObservedProduct.model_validate(response)
            if product.id != desired.external_id or product.type != desired.kind:
                raise ContentDeliveryError("content_target_changed")
            images = product.images
        by_media = {v.media_id: v.sha256 for v in checksums}
        result: dict[UUID, int] = {}
        for actual, reference in zip(images, desired.media):
            digest = by_media.get(reference.media_id)
            if reference.remote_id is not None or not actual.src or digest is None:
                continue
            try:
                data = await self._http.request_bytes(actual.src)
            except VerificationFailure:
                continue
            if sha256(data).hexdigest() == digest:
                result[reference.media_id] = actual.id
        return result
