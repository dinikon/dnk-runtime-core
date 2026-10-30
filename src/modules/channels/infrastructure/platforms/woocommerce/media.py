import base64
from dataclasses import dataclass
from uuid import UUID

from pydantic import BaseModel, Field, ValidationError

from src.modules.channels.application.content_media.contracts import PreparedGallery
from src.modules.channels.domain.content_media.error import ContentMediaError
from src.modules.channels.domain.types import JsonObject
from src.modules.channels.infrastructure.http import JsonHttp
from src.modules.channels.infrastructure.platforms.woocommerce.models import (
    WooCommerceConfig,
    WooCommerceCredentials,
)


class WooAttachment(BaseModel):
    """Минимальный подтверждённый ответ изображения WooCommerce."""

    id: int = Field(gt=0, strict=True)
    alt: str = ""


class WooProductGallery(BaseModel):
    """Ответ товара; прочие поля не выходят из пакета."""

    images: tuple[WooAttachment, ...]


class WooVariationGallery(BaseModel):
    """Стандартный контракт одного изображения вариации."""

    image: WooAttachment | None = None


@dataclass(frozen=True, slots=True)
class WooMediaTransferResult:
    """Подтверждённое соответствие для record_media_transfer_result."""

    media_id: UUID
    remote_id: str


class WooGalleryAdapter:
    """Формирует images-only обновление: повтор использует ID и не передаёт src."""

    def __init__(self, http: JsonHttp) -> None:
        """Получает существующий безопасный HTTP transport платформы."""
        self._http = http

    def payload(
        self, gallery: PreparedGallery, reserved_media_ids: tuple[UUID, ...]
    ) -> JsonObject:
        """Не теряет изображения при ограничениях вариации и не загружает без резервации."""
        images: list[JsonObject] = []
        for image in gallery.images:
            if image.caption:
                raise ContentMediaError("media_caption_unsupported")
            value: JsonObject = {"alt": image.alt}
            if image.remote_media_id is not None:
                if (
                    not image.remote_media_id.isdecimal()
                    or int(image.remote_media_id) <= 0
                ):
                    raise ContentMediaError("media_remote_id_invalid")
                value["id"] = int(image.remote_media_id)
            else:
                if image.media_id not in reserved_media_ids:
                    raise ContentMediaError(
                        "media_transfer_not_reserved", conflict=True
                    )
                value["src"] = image.url
            images.append(value)
        if gallery.publication_kind == "variant":
            if len(images) > 1:
                raise ContentMediaError("media_variation_gallery_unsupported")
            return {"image": images[0] if images else {"id": 0}}
        return {"images": images}

    async def update(
        self,
        *,
        config: WooCommerceConfig,
        credentials: WooCommerceCredentials,
        gallery: PreparedGallery,
        reserved_media_ids: tuple[UUID, ...],
    ) -> tuple[WooMediaTransferResult, ...]:
        """Вызывается вне SQL после begin; неоднозначная ошибка требует фиксации unknown."""
        body = self.payload(gallery, reserved_media_ids)
        if not gallery.external_id.isdecimal() or int(gallery.external_id) <= 0:
            raise ContentMediaError("media_target_invalid")
        path = "/products/" + gallery.external_id
        if gallery.publication_kind == "variant":
            parent = gallery.parent_external_id
            if parent is None or not parent.isdecimal() or int(parent) <= 0:
                raise ContentMediaError("media_target_invalid")
            path = f"/products/{parent}/variations/{gallery.external_id}"
        basic = base64.b64encode(
            (
                credentials.consumer_key.get_secret_value()
                + ":"
                + credentials.consumer_secret.get_secret_value()
            ).encode()
        ).decode()
        response = await self._http.request(
            "PUT",
            config.endpoint + "/wp-json/wc/v3" + path,
            headers={"Authorization": "Basic " + basic},
            body=body,
        )
        try:
            if gallery.publication_kind == "variant":
                image = WooVariationGallery.model_validate(response).image
                observed = (image,) if image is not None else ()
            else:
                observed = WooProductGallery.model_validate(response).images
        except ValidationError:
            raise ContentMediaError("media_provider_response_invalid") from None
        if len(observed) != len(gallery.images) or any(
            actual.alt != desired.alt
            for actual, desired in zip(observed, gallery.images)
        ):
            raise ContentMediaError("media_provider_response_invalid")
        return tuple(
            WooMediaTransferResult(desired.media_id, str(actual.id))
            for actual, desired in zip(observed, gallery.images)
        )
