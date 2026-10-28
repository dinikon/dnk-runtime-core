"""Чтение простых товаров, карточек и вариаций WooCommerce."""

import base64
from urllib.parse import urlencode

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

from src.modules.channels.application.error import VerificationFailure
from src.modules.channels.application.sync_run.port.source import (
    PublicationCheckpoint,
    PublicationReadPhase,
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
from src.modules.channels.infrastructure.platforms.woocommerce.models import (
    WooCommerceConfig,
    WooCommerceCredentials,
)


class WooPublicationCursor(BaseModel):
    """Курсор страницы и наблюдаемая валюта магазина."""

    model_config = ConfigDict(extra="forbid", strict=True)
    page: int = Field(default=1, ge=1)
    source_currency: str | None = None
    metadata_loaded: bool = False


class WooImage(BaseModel):
    """Первое изображение, если оно действительно возвращено API."""

    src: str | None = None


class WooPublication(BaseModel):
    """Поддержанные поля позиции без ограничения расширений raw_data."""

    model_config = ConfigDict(strict=True)
    id: int = Field(gt=0)
    type: str | None = None
    name: str | None = None
    sku: str | None = None
    permalink: str | None = None
    price: str | int | float | None = None
    regular_price: str | int | float | None = None
    sale_price: str | int | float | None = None
    stock_quantity: str | int | float | None = None
    manage_stock: bool | str = False
    stock_status: str | None = None
    status: str | None = None
    virtual: bool = False
    downloadable: bool = False
    images: list[WooImage] = Field(default_factory=list)
    image: WooImage | None = None


class WooPublicationReader:
    """Обходит продукты и затем детей по одному родителю без списка в checkpoint."""

    def __init__(self, http: JsonHttp) -> None:
        """Получает transport с заголовками пагинации."""
        self.http = http

    def normalize(
        self,
        raw: JsonObject,
        *,
        config: WooCommerceConfig,
        parent_id: str | None,
        source_currency: str | None,
    ) -> PublicationObservation:
        """Разделяет собственный и родительский остаток, не наследуя пустые поля."""
        product = WooPublication.model_validate(raw)
        kind = PublicationKind.VARIANT if parent_id else PublicationKind(product.type)
        mode = (
            "parent"
            if product.manage_stock == "parent"
            else "own" if product.manage_stock is True else "untracked"
        )
        image = (
            product.image
            if parent_id
            else product.images[0] if product.images else None
        )
        data = PublicationData(
            titles=(PublicationTitle(config.settings.locale, product.name),),
            currency=config.settings.currency,
            sku=product.sku,
            url=product.permalink,
            main_image_url=image.src if image else None,
            price=(
                None
                if kind is PublicationKind.VARIABLE
                else decimal_value(product.price)
            ),
            regular_price=(
                None
                if kind is PublicationKind.VARIABLE
                else decimal_value(product.regular_price)
            ),
            sale_price=(
                None
                if kind is PublicationKind.VARIABLE
                else decimal_value(product.sale_price)
            ),
            quantity=decimal_value(product.stock_quantity) if mode == "own" else None,
            stock_mode=mode,
            availability={
                "instock": "in_stock",
                "outofstock": "out_of_stock",
                "onbackorder": "on_order",
            }.get(product.stock_status),
            status=product.status,
            inherit_title=parent_id is not None and product.name is None,
        )
        return PublicationObservation(
            "variation" if parent_id else "product",
            str(product.id),
            kind,
            parent_id,
            "product" if parent_id else None,
            raw,
            data,
            "woocommerce.publication.v1",
            {
                "product_type": "variation" if parent_id else product.type,
                "parent_product_id": parent_id,
                "virtual": product.virtual,
                "downloadable": product.downloadable,
                "manage_stock": product.manage_stock,
                "source_currency": source_currency,
                "attributes": raw.get("attributes"),
                "variation_ids": raw.get("variations"),
            },
        )

    async def read(
        self,
        *,
        config: WooCommerceConfig,
        credentials: WooCommerceCredentials,
        checkpoint: PublicationCheckpoint,
        parent_external_id: str | None,
    ) -> PublicationPage:
        """Читает одну страницу API с ограниченным состоянием продолжения."""
        cursor = WooPublicationCursor.model_validate(checkpoint.cursor or {})
        basic = base64.b64encode(
            (
                credentials.consumer_key.get_secret_value()
                + ":"
                + credentials.consumer_secret.get_secret_value()
            ).encode()
        ).decode()
        headers = {"Authorization": "Basic " + basic}
        currency = cursor.source_currency
        if not cursor.metadata_loaded:
            metadata = await self.http.request(
                "GET", config.endpoint + "/wp-json/wc/v3/system_status", headers=headers
            )
            if isinstance(metadata, dict) and isinstance(
                metadata.get("settings"), dict
            ):
                currency = metadata["settings"].get("currency")
                if currency is not None and not isinstance(currency, str):
                    raise VerificationFailure("provider_response_invalid")
        children = checkpoint.phase is PublicationReadPhase.CHILDREN
        if children and parent_external_id is None:
            return PublicationPage((), (), checkpoint, True, 0)
        if children and (
            not parent_external_id.isdigit() or int(parent_external_id) < 1
        ):
            raise VerificationFailure("publication_identity_invalid")
        path = "/wp-json/wc/v3/products"
        if children:
            path += "/" + parent_external_id + "/variations"
        query = urlencode(
            {
                "per_page": 100,
                "page": cursor.page,
                "status": "any",
                "orderby": "id",
                "order": "asc",
            }
        )
        response = await self.http.request_response(
            "GET", config.endpoint + path + "?" + query, headers=headers
        )
        records = TypeAdapter(list[JsonObject]).validate_python(response.data)
        observations, skipped = [], 0
        for raw in records:
            if not children and raw.get("type") not in {"simple", "variable"}:
                skipped += 1
                continue
            observations.append(
                self.normalize(
                    raw,
                    config=config,
                    parent_id=parent_external_id if children else None,
                    source_currency=currency,
                )
            )
        total_pages = response.headers.get("x-wp-totalpages")
        if total_pages is not None and (
            not total_pages.isdigit() or int(total_pages) < 0
        ):
            raise VerificationFailure("provider_response_invalid")
        last_page = (
            cursor.page >= int(total_pages)
            if total_pages is not None
            else len(records) < 100
        )
        next_cursor = {
            "page": cursor.page + 1,
            "source_currency": currency,
            "metadata_loaded": True,
        }
        if last_page:
            next_cursor["page"] = 1
            next_checkpoint = PublicationCheckpoint(
                PublicationReadPhase.CHILDREN,
                next_cursor,
                parent_external_id if children else None,
                None,
            )
        else:
            next_checkpoint = PublicationCheckpoint(
                checkpoint.phase,
                next_cursor,
                checkpoint.after_parent,
                parent_external_id if children else None,
            )
        return PublicationPage(
            tuple(observations), (), next_checkpoint, False, len(records), skipped
        )
