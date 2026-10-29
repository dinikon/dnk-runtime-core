import base64
from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field, TypeAdapter, field_validator
from src.modules.channels.infrastructure.platforms.woocommerce.publications import (
    WooPublication,
    WooPublicationReader,
)
from src.modules.channels.infrastructure.platforms.woocommerce.models import (
    WooCommerceConfig,
    WooCommerceCredentials,
)
from src.modules.channels.infrastructure.http import JsonHttp
from src.modules.channels.domain.types import JsonObject
from src.modules.channels.domain.external_publication.value_object import decimal_value
from src.modules.channels.application.error import VerificationFailure
from src.modules.channels.application.external_publication.catalog_details import (
    PublicationLookup,
    PublicationDetails,
    PublicationProductDetails,
    PublicationTranslationDetails,
)


class WooProductDetails(WooPublication):
    """Нативные поля полного ответа продукта и вариации."""

    description: str | None = None
    backorders: str = "no"
    weight: str | None = None
    dimensions: dict[str, str] = Field(default_factory=dict)
    variations: list[int] = Field(default_factory=list)
    date_on_sale_from_gmt: datetime | None = None
    date_on_sale_to_gmt: datetime | None = None

    @field_validator("date_on_sale_from_gmt", "date_on_sale_to_gmt", mode="before")
    @classmethod
    def sale_time_utc(cls, value: object) -> object:
        """Поля GMT в REST API без offset всё равно обозначают UTC."""
        if isinstance(value, str):
            value = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if isinstance(value, datetime):
            return (
                value.replace(tzinfo=UTC)
                if value.tzinfo is None
                else value.astimezone(UTC)
            )
        return value


class WooMeasurementSetting(BaseModel):
    """Единицы измерений из настроек товаров WooCommerce REST API v3."""

    id: Literal["woocommerce_weight_unit", "woocommerce_dimension_unit"]
    value: str = Field(strict=True)


class WooDetailsReader:
    """Получает контейнер и все страницы вариаций по официальному REST API v3."""

    def __init__(self, http: JsonHttp) -> None:
        """Получает тот же безопасный transport, что и синхронизация."""
        self.http = http

    async def read(
        self,
        *,
        config: WooCommerceConfig,
        credentials: WooCommerceCredentials,
        publications: tuple[PublicationLookup, ...],
    ) -> PublicationDetails:
        """Не использует сохранённый raw вместо актуального ответа API."""
        root = next(p for p in publications if p.parent_id is None)
        if not root.external_id.isdigit():
            raise VerificationFailure("publication_identity_invalid")
        auth = base64.b64encode(
            (
                credentials.consumer_key.get_secret_value()
                + ":"
                + credentials.consumer_secret.get_secret_value()
            ).encode()
        ).decode()
        headers = {"Authorization": "Basic " + auth}
        base = config.endpoint + "/wp-json/wc/v3"
        raw = TypeAdapter(JsonObject).validate_python(
            await self.http.request(
                "GET", base + "/products/" + root.external_id, headers=headers
            )
        )
        native = WooProductDetails.model_validate(raw)
        if str(native.id) != root.external_id or native.type not in {
            "simple",
            "variable",
        }:
            raise VerificationFailure("publication_structure_changed")
        records: list[tuple[JsonObject, str | None]] = [(raw, None)]
        if native.type == "variable":
            seen: set[int] = set()
            for page in range(1, 1001):
                response = await self.http.request_response(
                    "GET",
                    base
                    + f"/products/{native.id}/variations?per_page=100&page={page}&status=any&orderby=id&order=asc",
                    headers=headers,
                )
                batch = TypeAdapter(list[JsonObject]).validate_python(response.data)
                ids = [WooProductDetails.model_validate(v).id for v in batch]
                if len(set(ids)) != len(ids) or set(ids) & seen:
                    raise VerificationFailure("pagination_not_progressing")
                seen.update(ids)
                records.extend((v, str(native.id)) for v in batch)
                pages = response.headers.get("x-wp-totalpages")
                if pages is not None and not pages.isdigit():
                    raise VerificationFailure("provider_response_invalid")
                if (pages is not None and page >= int(pages)) or (
                    pages is None and len(batch) < 100
                ):
                    break
            else:
                raise VerificationFailure("pagination_not_progressing")
            if set(native.variations) != seen:
                raise VerificationFailure("publication_structure_changed")
        products = [WooProductDetails.model_validate(value) for value, _ in records]
        units: dict[str, str] = {}
        if any(p.weight or any(p.dimensions.values()) for p in products):
            settings = TypeAdapter(list[JsonObject]).validate_python(
                await self.http.request(
                    "GET", base + "/settings/products", headers=headers
                )
            )
            for value in settings:
                if value.get("id") in {
                    "woocommerce_weight_unit",
                    "woocommerce_dimension_unit",
                }:
                    setting = WooMeasurementSetting.model_validate(value)
                    if setting.id in units:
                        raise VerificationFailure("provider_response_invalid")
                    units[setting.id] = setting.value
        weight_unit = units.get("woocommerce_weight_unit")
        dimension_unit = units.get("woocommerce_dimension_unit")
        warnings: list[str] = []
        result = []
        for (value, parent), product in zip(records, products):
            observation = WooPublicationReader(self.http).normalize(
                value, config=config, parent_id=parent, source_currency=None
            )
            data = observation.data
            priced = observation.kind.value != "variable"
            tracked = product.manage_stock is True
            status = {
                "in_stock": "in_stock",
                "out_of_stock": "out_of_stock",
                "on_order": "on_backorder",
            }.get(data.availability)
            if product.weight and weight_unit not in {"kg", "g"}:
                warnings.append(
                    "Масса не перенесена: единица источника не поддерживается."
                )
            if any(product.dimensions.values()) and dimension_unit not in {"cm", "m"}:
                warnings.append(
                    "Размеры не перенесены: единица источника не поддерживается."
                )
            images = (
                ((product.image.src,) if product.image and product.image.src else ())
                if parent
                else tuple(i.src for i in product.images if i.src)
            )
            result.append(
                PublicationProductDetails(
                    observation.resource_type,
                    observation.external_id,
                    parent,
                    observation.kind.value,
                    product.sku or None,
                    (
                        PublicationTranslationDetails(
                            config.settings.locale,
                            product.name,
                            (
                                product.description
                                if not parent or product.description
                                else None
                            ),
                        ),
                    ),
                    images,
                    tracked,
                    decimal_value(product.stock_quantity) if tracked else None,
                    (
                        None
                        if tracked
                        else status
                        or (
                            "in_stock" if parent or product.type == "variable" else None
                        )
                    ),
                    product.backorders if tracked else "no",
                    product.virtual,
                    (
                        decimal_value(product.weight)
                        if weight_unit in {"kg", "g"}
                        else None
                    ),
                    weight_unit if weight_unit in {"kg", "g"} else None,
                    (
                        decimal_value(product.dimensions.get("length"))
                        if dimension_unit in {"cm", "m"}
                        else None
                    ),
                    (
                        decimal_value(product.dimensions.get("width"))
                        if dimension_unit in {"cm", "m"}
                        else None
                    ),
                    (
                        decimal_value(product.dimensions.get("height"))
                        if dimension_unit in {"cm", "m"}
                        else None
                    ),
                    dimension_unit if dimension_unit in {"cm", "m"} else None,
                    regular_price=(
                        (
                            data.regular_price
                            if data.regular_price is not None
                            else data.price
                        )
                        if priced
                        else None
                    ),
                    currency=config.settings.currency if priced else None,
                    sale_price=data.sale_price if priced else None,
                    date_on_sale_from=product.date_on_sale_from_gmt if priced else None,
                    date_on_sale_to=product.date_on_sale_to_gmt if priced else None,
                )
            )
        return PublicationDetails(tuple(result), tuple(dict.fromkeys(warnings)))
