"""Чтение всех текущих и архивных позиций продавца Rozetka."""

from urllib.parse import urlencode
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from src.modules.channels.application.error import VerificationFailure
from src.modules.channels.application.sync_run.port.source import (
    PublicationCheckpoint,
    PublicationObservation,
    PublicationPage,
)
from src.modules.channels.domain.external_publication.value_object import (
    PublicationData,
    PublicationKind,
    PublicationTitle,
    decimal_value,
)
from src.modules.channels.domain.types import JsonObject
from src.modules.channels.infrastructure.http import JsonHttp
from src.modules.channels.infrastructure.platforms.rozetka.models import (
    RozetkaConfig,
    RozetkaCredentials,
)


class RozetkaPublicationCursor(BaseModel):
    """Этап и страница принадлежат пакету площадки."""

    model_config = ConfigDict(extra="forbid", strict=True)
    stream: Literal["all", "archive"] = "all"
    page: int = Field(default=1, ge=1)


class RozetkaPublication(BaseModel):
    """Разбирает ключ источника, не требуя уже опубликованного rz_item_id."""

    model_config = ConfigDict(strict=True)
    sync_source_id: int = Field(gt=0)
    price_offer_id: str = Field(min_length=1)
    item_id: int | None = None
    rz_item_id: int | None = None
    name_ua: str | None = None
    name_ru: str | None = None
    article: str | None = None
    price: str | int | float | None = None
    price_old: str | int | float | None = None
    price_promo: str | int | float | None = None
    stock_quantity: str | int | float | None = None
    available: int | None = None
    upload_status: int | None = None
    url: str | None = None
    photo: list[str] = Field(default_factory=list)
    photo_preview: list[str] = Field(default_factory=list)


class RozetkaPageMeta(BaseModel):
    """Использует фактическую пагинацию, включая ограничение pageSize сервером."""

    currentPage: int = Field(ge=1)
    pageCount: int = Field(ge=0)


class RozetkaPageContent(BaseModel):
    """Страница списка либо архива."""

    items: list[JsonObject]
    meta: RozetkaPageMeta = Field(alias="_meta")


class RozetkaPublicationResponse(BaseModel):
    """HTTP 200 с success=false не является успешным импортом."""

    success: bool = Field(strict=True)
    content: RozetkaPageContent | None = None
    errors: JsonObject | None = None


class RozetkaPublicationReader:
    """Последовательно обходит два потока без фильтрации скрытых позиций."""

    def __init__(self, http: JsonHttp) -> None:
        """Получает безопасный transport."""
        self.http = http

    def normalize(
        self, raw: JsonObject, config: RozetkaConfig
    ) -> PublicationObservation:
        """Сохраняет нативные идентификаторы отдельно от стабильного ключа прайса."""
        product = RozetkaPublication.model_validate(raw)
        images = product.photo or product.photo_preview
        data = PublicationData(
            titles=(
                PublicationTitle("uk", product.name_ua),
                PublicationTitle("ru", product.name_ru),
            ),
            currency=config.settings.currency,
            sku=product.article,
            url=product.url,
            main_image_url=images[0] if images else None,
            price=decimal_value(product.price),
            regular_price=decimal_value(product.price_old),
            sale_price=decimal_value(product.price_promo),
            quantity=decimal_value(product.stock_quantity),
            stock_mode="own",
            availability={0: "out_of_stock", 1: "in_stock", 2: "removed"}.get(
                product.available
            ),
            status=(
                str(product.upload_status)
                if product.upload_status is not None
                else None
            ),
        )
        return PublicationObservation(
            "source_offer",
            f"{product.sync_source_id}:{product.price_offer_id}",
            PublicationKind.SIMPLE,
            None,
            None,
            raw,
            data,
            "rozetka.publication.v1",
            {
                "sync_source_id": product.sync_source_id,
                "price_offer_id": product.price_offer_id,
                "item_id": product.item_id,
                "rz_item_id": product.rz_item_id,
                "group_id": raw.get("group_id"),
                "rz_group_id": raw.get("rz_group_id"),
                "upload_status": product.upload_status,
                "upload_status_title": raw.get("upload_status_title"),
                "source_currency": raw.get("currency", "UAH"),
            },
        )

    async def read(
        self,
        *,
        config: RozetkaConfig,
        credentials: RozetkaCredentials,
        checkpoint: PublicationCheckpoint,
    ) -> PublicationPage:
        """Читает страницу списка или архива без фильтра наличия."""
        cursor = RozetkaPublicationCursor.model_validate(checkpoint.cursor or {})
        query = urlencode({"page": cursor.page, "pageSize": 100})
        response = await self.http.request(
            "GET",
            config.endpoint + "/goods/" + cursor.stream + "?" + query,
            headers={"Authorization": "Bearer " + credentials.token.get_secret_value()},
        )
        page = RozetkaPublicationResponse.model_validate(response)
        if not page.success:
            code = (page.errors or {}).get("message")
            raise VerificationFailure(
                "invalid_credentials"
                if code == "invalid_credentials"
                else (
                    "permission_missing"
                    if code in {"access_denied", "forbidden"}
                    else "provider_response_invalid"
                )
            )
        if page.content is None or page.content.meta.currentPage != cursor.page:
            raise VerificationFailure("provider_response_invalid")
        last = cursor.page >= page.content.meta.pageCount
        done = last and cursor.stream == "archive"
        next_cursor = {
            "stream": "archive" if last else cursor.stream,
            "page": 1 if last else cursor.page + 1,
        }
        return PublicationPage(
            tuple(self.normalize(raw, config) for raw in page.content.items),
            (),
            PublicationCheckpoint(cursor=next_cursor),
            done,
            len(page.content.items),
        )
