import json
import base64
import re
from hashlib import sha256
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from src.modules.channels.application.content_delivery.contracts import (
    ContentDeliveryResult,
    ContentMediaResult,
    ContentWriteOutcome,
    PreparedContentRequest,
)
from src.modules.channels.application.content_media.contracts import PreparedGallery
from src.modules.channels.application.error import VerificationFailure
from src.modules.channels.domain.content_delivery.error import ContentDeliveryError
from src.modules.channels.domain.content_delivery.value_object import DeliveryContextVO
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
            result = self.compare(value, observed, accept_new_media=False)
            if result is not None:
                return result
            if reconcile:
                return ContentDeliveryResult(
                    ContentWriteOutcome.UNKNOWN,
                    error_code="content_reconciliation_required",
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
            result = self.compare(value, response, accept_new_media=True)
            if result is not None:
                return result
            return ContentDeliveryResult(
                ContentWriteOutcome.UNKNOWN,
                error_code="content_provider_response_mismatch",
            )
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
        """Сверяет адрес, отправленные поля и порядок; alt не доказывает новую загрузку."""
        fields: list[str] = []
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
                    return None
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
                    return None
                fields.append("title")
            if product.description is not None:
                if woo_description(observed_product.description) != woo_description(
                    product.description
                ):
                    return None
                fields.append("body")
            images, wanted, has_gallery = (
                observed_product.images,
                product.images or (),
                product.images is not None,
            )
        media: list[ContentMediaResult] = []
        if has_gallery:
            if len(images) != len(wanted) or len(images) != len(desired.media):
                return None
            for actual, expected, reference in zip(images, wanted, desired.media):
                if (
                    actual.alt != (expected.alt or "")
                    or (
                        reference.remote_id is not None
                        and actual.id != reference.remote_id
                    )
                    or (reference.remote_id is None and not accept_new_media)
                ):
                    return None
                media.append(ContentMediaResult(reference.media_id, str(actual.id)))
            fields.append("gallery")
        return ContentDeliveryResult(
            ContentWriteOutcome.CONFIRMED, tuple(fields), tuple(media)
        )
