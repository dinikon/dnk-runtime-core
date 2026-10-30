from urllib.parse import urlencode

from pydantic import BaseModel, ConfigDict, Field

from src.modules.channels.application.error import VerificationFailure
from src.modules.channels.application.external_publication.catalog_details import (
    PublicationLookup,
)
from src.modules.channels.application.stock_sync.contracts import PlatformStockSnapshot
from src.modules.channels.domain.stock_sync.value_object import StockSnapshotVO
from src.modules.channels.domain.external_publication.value_object import decimal_value
from src.modules.channels.infrastructure.http import JsonHttp
from src.modules.channels.domain.types import JsonObject
from src.modules.channels.infrastructure.platforms.rozetka.models import (
    RozetkaConfig,
    RozetkaCredentials,
)


class RozetkaSourceStock(BaseModel):
    """Режим управления источником; он не переключается автоматически."""

    availability: int | None = None
    is_virtual_source: int | None = None


class RozetkaStockItem(BaseModel):
    """Разделяет ключ прайса, внутренний ID и подтверждённый marketplace ID."""

    model_config = ConfigDict(strict=True)
    sync_source_id: int = Field(gt=0)
    price_offer_id: str
    item_id: int | None = None
    rz_item_id: int | None = None
    stock_quantity: int | None = None
    available: int | None = None
    sync_source: RozetkaSourceStock | None = None


class RozetkaStockContent(BaseModel):
    """Варианты официального envelope деталей."""

    item: RozetkaStockItem | list[RozetkaStockItem]


class RozetkaStockResponse(BaseModel):
    """Сохраняет ошибки провайдера внутри пакета."""

    success: bool = Field(strict=True)
    content: RozetkaStockContent | None = None
    errors: JsonObject | None = None


class RozetkaStock:
    """Читает goods/details и записывает только stock_quantity через mass-update."""

    def __init__(self, http: JsonHttp) -> None:
        """Получает transport без парольного fallback."""
        self.http = http

    async def get(
        self,
        *,
        config: RozetkaConfig,
        credentials: RozetkaCredentials,
        publication: PublicationLookup,
        parent: PublicationLookup | None = None,
    ) -> PlatformStockSnapshot:
        """Сверяет стабильную идентичность; удаление из прайса не означает ноль."""
        item_id, rz_id = publication.platform_data.get(
            "item_id"
        ), publication.platform_data.get("rz_item_id")
        params = (
            {"item_id": item_id}
            if type(item_id) is int and item_id > 0
            else {"rz_item_id": rz_id} if type(rz_id) is int and rz_id > 0 else None
        )
        if publication.resource_type != "source_offer" or params is None:
            raise VerificationFailure("publication_details_unavailable")
        source = publication.platform_data.get("sync_source_id")
        if type(source) is int and source > 0:
            params["sync_source_id"] = source
        response = RozetkaStockResponse.model_validate(
            await self.http.request(
                "GET",
                config.endpoint + "/goods/details?" + urlencode(params),
                headers={
                    "Authorization": "Bearer " + credentials.token.get_secret_value()
                },
            )
        )
        if not response.success:
            code = (response.errors or {}).get("message")
            raise VerificationFailure(
                "permission_missing"
                if code in {"access_denied", "forbidden"}
                else "provider_response_invalid"
            )
        if response.content is None:
            raise VerificationFailure("provider_response_invalid")
        records = (
            response.content.item
            if isinstance(response.content.item, list)
            else [response.content.item]
        )
        if len(records) != 1:
            raise VerificationFailure("publication_identity_invalid")
        value = records[0]
        if f"{value.sync_source_id}:{value.price_offer_id}" != publication.external_id:
            raise VerificationFailure("publication_identity_invalid")
        return PlatformStockSnapshot(
            StockSnapshotVO(
                "source_offer",
                publication.external_id,
                "own",
                decimal_value(value.stock_quantity),
                {0: "out_of_stock", 1: "in_stock", 2: "removed"}.get(value.available),
            ),
            {
                "item_id": value.item_id,
                "rz_item_id": value.rz_item_id,
                "stock_quantity": value.stock_quantity,
                "available": value.available,
                "source_availability": (
                    value.sync_source.availability if value.sync_source else None
                ),
            },
        )

    async def set(
        self,
        *,
        config: RozetkaConfig,
        credentials: RozetkaCredentials,
        publication: PublicationLookup,
        quantity: int,
        backorders: str,
    ) -> PlatformStockSnapshot:
        """Не меняет режим источника и не выдаёт локальный ключ прайса за ID записи."""
        if backorders != "no":
            raise VerificationFailure("stock_backorders_unsupported")
        before = await self.get(
            config=config, credentials=credentials, publication=publication
        )
        rz_id = before.platform_data.get("rz_item_id")
        if type(rz_id) is not int or rz_id < 1:
            raise VerificationFailure("stock_write_identity_unavailable")
        stored_id = publication.platform_data.get("rz_item_id")
        if type(stored_id) is int and stored_id > 0 and stored_id != rz_id:
            raise VerificationFailure("stock_ownership_ambiguous")
        if before.platform_data.get("source_availability") != 4:
            raise VerificationFailure("stock_source_api_required")
        response = await self.http.request(
            "PUT",
            config.endpoint + "/items/mass-update",
            headers={"Authorization": "Bearer " + credentials.token.get_secret_value()},
            body={"items": [{"item_rz_id": rz_id, "stock_quantity": quantity}]},
        )
        if (
            not isinstance(response, dict)
            or response.get("success") is not True
            or response.get("errors")
        ):
            code = (
                response.get("errors", {}).get("message")
                if isinstance(response, dict)
                and isinstance(response.get("errors"), dict)
                else None
            )
            raise VerificationFailure(
                "permission_missing"
                if code in {"access_denied", "forbidden"}
                else "stock_write_rejected"
            )
        result = await self.get(
            config=config, credentials=credentials, publication=publication
        )
        if result.stock.quantity != quantity:
            raise VerificationFailure("stock_write_unconfirmed", retryable=True)
        return result


def known_stock_target(native: JsonObject) -> str | None:
    """Один marketplace ID может оставаться в нескольких архивных источниках прайса."""
    identifier = native.get("rz_item_id")
    return (
        f"rozetka.item:{identifier}"
        if type(identifier) is int and identifier > 0
        else None
    )
