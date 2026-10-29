import re
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from typing import Literal
from zoneinfo import ZoneInfo

from pydantic import BaseModel, Field, field_validator
from src.modules.channels.infrastructure.platforms.prom.publications import (
    PromProduct,
    PromProductResponse,
    PromPublicationReader,
)
from src.modules.channels.infrastructure.platforms.prom.models import (
    PromConfig,
    PromCredentials,
)
from src.modules.channels.application.sync_run.port.source import PublicationCheckpoint
from src.modules.channels.infrastructure.http import JsonHttp
from src.modules.channels.application.error import VerificationFailure
from src.modules.channels.application.external_publication.catalog_details import (
    PublicationLookup,
    PublicationDetails,
    PublicationProductDetails,
    PublicationTranslationDetails,
)


class PromDetailImage(BaseModel):
    """URL изображения, возвращённый Prom, в том числе уменьшенной копии."""

    url: str


class PromDiscount(BaseModel):
    """Скидка Prom и календарные даты по времени Украины."""

    value: Decimal = Field(ge=0)
    type: Literal["amount", "percent"]
    date_start: date | None = Field(default=None, strict=True)
    date_end: date | None = Field(default=None, strict=True)

    @field_validator("date_start", "date_end", mode="before")
    @classmethod
    def calendar_date(cls, value: object) -> object:
        """Читает документированный формат DD.MM.YYYY без угадывания timezone."""
        if isinstance(value, str):
            return datetime.strptime(value, "%d.%m.%Y").date() if value else None
        return value


class PromProductDetails(PromProduct):
    """Контент полного ответа Prom с независимыми переводами."""

    description_multilang: dict[str, str | None] = Field(default_factory=dict)
    images: list[PromDetailImage] = Field(default_factory=list)
    discount: PromDiscount | None = None

    @property
    def original_image_urls(self) -> tuple[str, ...]:
        """Убирает размер копии в ссылках CDN Prom для скачивания исходных файлов."""
        urls = tuple(image.url for image in self.images) or (
            (self.main_image,) if self.main_image else ()
        )
        return tuple(
            re.sub(
                r"^(https?://images\.prom\.ua/[0-9]+)_w[0-9]+_h[0-9]+_",
                r"\1_",
                url,
                count=1,
                flags=re.IGNORECASE,
            )
            for url in urls
        )


class PromDetailsReader:
    """Получает актуальные товары, сохраняя продаваемую роль основного товара."""

    def __init__(self, http: JsonHttp) -> None:
        """Получает общий transport Prom."""
        self.http = http

    async def read(
        self,
        *,
        config: PromConfig,
        credentials: PromCredentials,
        publications: tuple[PublicationLookup, ...],
    ) -> PublicationDetails:
        """Обнаруживает семейство через список и затем читает полные ответы его позиций."""
        root = next(p for p in publications if p.parent_id is None)
        if not root.external_id.isdigit():
            raise VerificationFailure("publication_identity_invalid")
        reader = PromPublicationReader(self.http)
        headers = {
            "Authorization": "Bearer " + credentials.token.get_secret_value(),
            "X-LANGUAGE": "uk",
        }
        root_raw = PromProductResponse.model_validate(
            await self.http.request(
                "GET",
                config.endpoint + "/api/v1/products/" + root.external_id,
                headers=headers,
            )
        ).product
        native_root = PromProductDetails.model_validate(root_raw)
        family: set[str] = {root.external_id}
        if (
            len(publications) > 1
            or native_root.is_variation
            or native_root.variation_group_id is not None
        ):
            checkpoint = PublicationCheckpoint()
            for _ in range(1000):
                page = await reader.read(
                    config=config, credentials=credentials, checkpoint=checkpoint
                )
                family.update(
                    p.external_id
                    for p in page.items
                    if p.parent_external_id == root.external_id
                )
                if page.done:
                    break
                checkpoint = page.checkpoint
            else:
                raise VerificationFailure("pagination_not_progressing")
        result = []
        for external_id in sorted(family, key=int):
            raw = (
                root_raw
                if external_id == root.external_id
                else PromProductResponse.model_validate(
                    await self.http.request(
                        "GET",
                        config.endpoint + "/api/v1/products/" + external_id,
                        headers=headers,
                    )
                ).product
            )
            native = PromProductDetails.model_validate(raw)
            observation = reader.normalize(raw, config)
            if observation.external_id != external_id:
                raise VerificationFailure("publication_identity_invalid")
            data = observation.data
            translations = tuple(
                PublicationTranslationDetails(
                    code,
                    next((t.title for t in data.titles if t.locale == code), None),
                    (
                        native.description_multilang.get(
                            "uk", native.description_multilang.get("ua")
                        )
                        if code == "uk"
                        else native.description_multilang.get("ru")
                    ),
                )
                for code in ("uk", "ru")
            )
            tracked = data.quantity is not None
            status = {
                "in_stock": "in_stock",
                "out_of_stock": "out_of_stock",
                "on_order": "on_backorder",
                "not_applicable": "in_stock",
            }.get(data.availability)
            sale_price, sale_from, sale_to = None, None, None
            if data.price is not None and native.discount is not None:
                discount = native.discount
                reduction = (
                    data.price * discount.value / Decimal(100)
                    if discount.type == "percent"
                    else discount.value
                )
                sale_price = data.price - reduction
                zone = ZoneInfo("Europe/Kyiv")
                if discount.date_start is not None:
                    sale_from = datetime.combine(
                        discount.date_start, time.min, zone
                    ).astimezone(UTC)
                if discount.date_end is not None:
                    sale_to = datetime.combine(
                        discount.date_end + timedelta(days=1), time.min, zone
                    ).astimezone(UTC)
            result.append(
                PublicationProductDetails(
                    "product",
                    external_id,
                    observation.parent_external_id,
                    observation.kind.value,
                    native.sku or None,
                    translations,
                    native.original_image_urls,
                    tracked,
                    data.quantity if tracked else None,
                    None if tracked else status,
                    virtual=native.selling_type == "service",
                    regular_price=data.price,
                    currency=config.settings.currency,
                    sale_price=sale_price,
                    date_on_sale_from=sale_from,
                    date_on_sale_to=sale_to,
                )
            )
        return PublicationDetails(tuple(result))
