"""Постраничное чтение Prom и восстановление реальных основных товаров."""

from urllib.parse import urlencode

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
from src.modules.channels.infrastructure.platforms.prom.models import (
    PromConfig,
    PromCredentials,
)


class PromProduct(BaseModel):
    """Разбирает используемые поля, не отбрасывая исходный объект хранения."""

    model_config = ConfigDict(strict=True)
    id: int = Field(gt=0)
    external_id: str | None = None
    name: str | None = None
    name_multilang: dict[str, str | None] = Field(default_factory=dict)
    sku: str | None = None
    price: str | int | float | None = None
    currency: str | None = None
    presence: str | None = None
    quantity_in_stock: str | int | float | None = None
    main_image: str | None = None
    url: str | None = None
    status: str | None = None
    selling_type: str | None = None
    is_variation: bool = False
    variation_base_id: int | None = Field(default=None, gt=0)
    variation_group_id: int | None = Field(default=None, gt=0)


class PromProductPage(BaseModel):
    """Отсутствующий products не считается пустым магазином."""

    products: list[JsonObject]


class PromProductResponse(BaseModel):
    """Ответ получения одного основного товара."""

    product: JsonObject


class PromPublicationCursor(BaseModel):
    """Курсор принадлежит только пакету Prom."""

    model_config = ConfigDict(extra="forbid", strict=True)
    last_id: int | None = Field(default=None, gt=0)


class PromPublicationReader:
    """Связывает нативные настройки и HTTP с общими наблюдениями Channels."""

    def __init__(self, http: JsonHttp) -> None:
        """Получает безопасный общий transport."""
        self.http = http

    def normalize(self, raw: JsonObject, config: PromConfig) -> PublicationObservation:
        """Сохраняет полный ответ и интерпретирует явную ссылку на основной товар."""
        product = PromProduct.model_validate(raw)
        parent = product.variation_base_id
        if parent == product.id:
            parent = None
        if (
            product.is_variation
            and parent is None
            and product.variation_base_id != product.id
        ):
            raise VerificationFailure("publication_parent_unavailable")
        service = product.selling_type == "service"
        data = PublicationData(
            titles=(
                PublicationTitle(
                    "uk",
                    product.name_multilang.get("uk", product.name_multilang.get("ua")),
                ),
                PublicationTitle("ru", product.name_multilang.get("ru")),
            ),
            currency=config.settings.currency,
            sku=product.sku,
            url=product.url,
            main_image_url=product.main_image,
            price=decimal_value(product.price),
            quantity=None if service else decimal_value(product.quantity_in_stock),
            stock_mode="not_applicable" if service else "own",
            availability={
                "available": "in_stock",
                "not_available": "out_of_stock",
                "order": "on_order",
                "service": "not_applicable",
            }.get(product.presence),
            status=product.status,
        )
        return PublicationObservation(
            "product",
            str(product.id),
            PublicationKind.VARIANT if parent else PublicationKind.SIMPLE,
            str(parent) if parent else None,
            "product" if parent else None,
            raw,
            data,
            "prom.publication.v1",
            {
                "is_variation": product.is_variation,
                "import_key": (
                    product.external_id
                    if product.external_id and product.external_id.strip()
                    else None
                ),
                "variation_base_id": product.variation_base_id,
                "variation_group_id": product.variation_group_id,
                "source_currency": product.currency,
                "selling_type": product.selling_type,
                "discount": raw.get("discount"),
                "prices": raw.get("prices"),
            },
        )

    async def read(
        self,
        *,
        config: PromConfig,
        credentials: PromCredentials,
        checkpoint: PublicationCheckpoint,
    ) -> PublicationPage:
        """Читает страницу и её отсутствующих в ответе основных товаров."""
        cursor = PromPublicationCursor.model_validate(checkpoint.cursor or {})
        query = {"limit": 100}
        if cursor.last_id is not None:
            query["last_id"] = cursor.last_id
        headers = {
            "Authorization": "Bearer " + credentials.token.get_secret_value(),
            "X-LANGUAGE": "uk",
        }
        response = await self.http.request(
            "GET",
            config.endpoint + "/api/v1/products/list?" + urlencode(query),
            headers=headers,
        )
        page = PromProductPage.model_validate(response)
        observations = tuple(self.normalize(raw, config) for raw in page.products)
        ids = {item.external_id for item in observations}
        missing = tuple(
            sorted(
                {
                    item.parent_external_id
                    for item in observations
                    if item.parent_external_id and item.parent_external_id not in ids
                }
            )
        )
        dependencies = await self.read_dependencies(
            config=config,
            credentials=credentials,
            keys=tuple(("product", key) for key in missing),
        )
        last = int(observations[-1].external_id) if observations else cursor.last_id
        if len(observations) >= 100 and last == cursor.last_id:
            raise VerificationFailure("pagination_not_progressing")
        return PublicationPage(
            observations,
            dependencies,
            PublicationCheckpoint(cursor={"last_id": last}),
            len(observations) < 100,
            len(observations),
        )

    async def read_dependencies(
        self,
        *,
        config: PromConfig,
        credentials: PromCredentials,
        keys: tuple[tuple[str, str], ...],
    ) -> tuple[PublicationObservation, ...]:
        """Дозагружает только явно запрошенные нативные ID."""
        observations = []
        for resource_type, external_id in keys:
            if (
                resource_type != "product"
                or not external_id.isdigit()
                or int(external_id) < 1
            ):
                raise VerificationFailure("publication_identity_invalid")
            response = await self.http.request(
                "GET",
                config.endpoint + "/api/v1/products/" + external_id,
                headers={
                    "Authorization": "Bearer " + credentials.token.get_secret_value(),
                    "X-LANGUAGE": "uk",
                },
            )
            item = self.normalize(
                PromProductResponse.model_validate(response).product, config
            )
            if item.external_id != external_id:
                raise VerificationFailure("publication_identity_invalid")
            observations.append(item)
        return tuple(observations)
