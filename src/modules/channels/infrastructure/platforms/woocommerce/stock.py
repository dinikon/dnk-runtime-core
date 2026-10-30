import base64

from pydantic import BaseModel, ConfigDict, Field

from src.modules.channels.application.error import VerificationFailure
from src.modules.channels.application.external_publication.catalog_details import (
    PublicationLookup,
)
from src.modules.channels.application.stock_sync.contracts import PlatformStockSnapshot
from src.modules.channels.domain.stock_sync.value_object import StockSnapshotVO
from src.modules.channels.domain.external_publication.value_object import decimal_value
from src.modules.channels.infrastructure.http import JsonHttp
from src.modules.channels.infrastructure.platforms.woocommerce.models import (
    WooCommerceConfig,
    WooCommerceCredentials,
)


class WooStockResponse(BaseModel):
    """Только поля количественного API; неизвестное количество сохраняется."""

    model_config = ConfigDict(strict=True)
    id: int = Field(gt=0)
    manage_stock: bool | str
    stock_quantity: int | None = None
    stock_status: str | None = None
    backorders: str | None = None


class WooStock:
    """Различает собственный остаток вариации и общий остаток контейнера."""

    def __init__(self, http: JsonHttp) -> None:
        """Получает общий безопасный transport."""
        self.http = http

    @staticmethod
    def headers(credentials: WooCommerceCredentials) -> dict[str, str]:
        """Помещает реальные значения ключей только в заголовок Basic."""
        basic = base64.b64encode(
            (
                credentials.consumer_key.get_secret_value()
                + ":"
                + credentials.consumer_secret.get_secret_value()
            ).encode()
        ).decode()
        return {"Authorization": "Basic " + basic}

    @staticmethod
    def path(publication: PublicationLookup) -> str:
        """Строит путь только из проверенных положительных нативных ID."""
        if not publication.external_id.isdigit() or int(publication.external_id) < 1:
            raise VerificationFailure("publication_identity_invalid")
        if publication.resource_type == "variation":
            parent = publication.platform_data.get("parent_product_id")
            if not isinstance(parent, str) or not parent.isdigit() or int(parent) < 1:
                raise VerificationFailure("publication_identity_invalid")
            return (
                "/wp-json/wc/v3/products/"
                + parent
                + "/variations/"
                + publication.external_id
            )
        if publication.resource_type != "product":
            raise VerificationFailure("publication_identity_invalid")
        return "/wp-json/wc/v3/products/" + publication.external_id

    async def get(
        self,
        *,
        config: WooCommerceConfig,
        credentials: WooCommerceCredentials,
        publication: PublicationLookup,
        parent: PublicationLookup | None = None,
    ) -> PlatformStockSnapshot:
        """Подтверждает владельца свежим ответом API, включая старые версии Woo."""
        raw = await self.http.request(
            "GET",
            config.endpoint + self.path(publication),
            headers=self.headers(credentials),
        )
        value = WooStockResponse.model_validate(raw)
        if str(value.id) != publication.external_id:
            raise VerificationFailure("publication_identity_invalid")
        if value.manage_stock not in {True, False, "parent"}:
            raise VerificationFailure("provider_response_invalid")
        if publication.resource_type == "variation" and value.manage_stock is not True:
            if parent is None:
                if value.manage_stock == "parent":
                    raise VerificationFailure("stock_ownership_ambiguous")
            else:
                ancestor = await self.get(
                    config=config, credentials=credentials, publication=parent
                )
                if ancestor.stock.mode == "own":
                    return ancestor
                if value.manage_stock == "parent":
                    raise VerificationFailure("stock_ownership_ambiguous")
        mode = "own" if value.manage_stock is True else "untracked"
        return PlatformStockSnapshot(
            StockSnapshotVO(
                publication.resource_type,
                str(value.id),
                mode,
                decimal_value(value.stock_quantity) if mode == "own" else None,
                {
                    "instock": "in_stock",
                    "outofstock": "out_of_stock",
                    "onbackorder": "on_order",
                }.get(value.stock_status),
                value.backorders,
            ),
            {
                "manage_stock": value.manage_stock,
                "stock_quantity": value.stock_quantity,
                "stock_status": value.stock_status,
                "backorders": value.backorders,
            },
        )

    async def set(
        self,
        *,
        config: WooCommerceConfig,
        credentials: WooCommerceCredentials,
        publication: PublicationLookup,
        quantity: int,
        backorders: str,
    ) -> PlatformStockSnapshot:
        """Не отправляет цену, контент и статус публикации."""
        if backorders not in {"no", "notify", "yes"}:
            raise VerificationFailure("stock_backorders_unsupported")
        raw = await self.http.request(
            "PUT",
            config.endpoint + self.path(publication),
            headers=self.headers(credentials),
            body={
                "manage_stock": True,
                "stock_quantity": quantity,
                "backorders": backorders,
            },
        )
        value = WooStockResponse.model_validate(raw)
        if str(value.id) != publication.external_id:
            raise VerificationFailure("publication_identity_invalid")
        result = await self.get(
            config=config, credentials=credentials, publication=publication
        )
        if (
            result.stock.mode != "own"
            or result.stock.quantity != quantity
            or result.stock.backorders != backorders
        ):
            raise VerificationFailure("stock_write_unconfirmed", retryable=True)
        return result
