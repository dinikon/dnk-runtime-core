import logging
import re

from pydantic import BaseModel, Field, ConfigDict

from src.modules.channels.domain.types import JsonObject
from src.modules.channels.application.error import VerificationFailure
from src.modules.channels.application.external_publication.catalog_details import (
    PublicationLookup,
)
from src.modules.channels.application.stock_sync.contracts import PlatformStockSnapshot
from src.modules.channels.domain.stock_sync.value_object import StockSnapshotVO
from src.modules.channels.domain.external_publication.value_object import decimal_value
from src.modules.channels.infrastructure.http import JsonHttp
from src.modules.channels.infrastructure.platforms.prom.models import (
    PromConfig,
    PromCredentials,
)
from src.modules.channels.infrastructure.platforms.prom.publications import (
    PromProductResponse,
    PromProduct,
)

logger = logging.getLogger(__name__)


class PromStockUpdate(BaseModel):
    """Ответ редактирования: пустые обработанные ID не означают отказ."""

    model_config = ConfigDict(strict=True)
    processed_ids: list[int]
    errors: JsonObject = Field(default_factory=dict)
    warnings: JsonObject = Field(default_factory=dict)


class PromStock:
    """Количественный API Prom без изменения цены и контента."""

    def __init__(self, http: JsonHttp) -> None:
        """Получает общий безопасный transport."""
        self.http = http

    async def get(
        self,
        *,
        config: PromConfig,
        credentials: PromCredentials,
        publication: PublicationLookup,
        parent: PublicationLookup | None = None,
    ) -> PlatformStockSnapshot:
        """Не угадывает наследование наличия разновидности при неизвестном количестве."""
        if (
            publication.resource_type != "product"
            or not publication.external_id.isdigit()
            or int(publication.external_id) < 1
        ):
            raise VerificationFailure("publication_identity_invalid")
        raw = PromProductResponse.model_validate(
            await self.http.request(
                "GET",
                config.endpoint + "/api/v1/products/" + publication.external_id,
                headers={
                    "Authorization": "Bearer " + credentials.token.get_secret_value()
                },
            )
        ).product
        value = PromProduct.model_validate(raw)
        if str(value.id) != publication.external_id:
            raise VerificationFailure("publication_identity_invalid")
        quantity = decimal_value(value.quantity_in_stock)
        mode = (
            "not_applicable"
            if value.selling_type == "service"
            else "unknown" if value.is_variation and quantity is None else "own"
        )
        return PlatformStockSnapshot(
            StockSnapshotVO(
                "product",
                str(value.id),
                mode,
                quantity,
                {
                    "available": "in_stock",
                    "not_available": "out_of_stock",
                    "order": "on_order",
                    "service": "not_applicable",
                }.get(value.presence),
            ),
            {
                "quantity_in_stock": raw.get("quantity_in_stock"),
                "presence": value.presence,
                "in_stock": raw.get("in_stock"),
            },
        )

    async def set(
        self,
        *,
        config: PromConfig,
        credentials: PromCredentials,
        publication: PublicationLookup,
        quantity: int,
        backorders: str,
    ) -> PlatformStockSnapshot:
        """Отклоняет явные ошибки и подтверждает фактический остаток чтением."""
        before = await self.get(
            config=config, credentials=credentials, publication=publication
        )
        if before.stock.mode != "own":
            raise VerificationFailure("stock_ownership_ambiguous")
        presence = (
            "available"
            if quantity > 0
            else "not_available" if backorders == "no" else "order"
        )
        response = PromStockUpdate.model_validate(
            await self.http.request(
                "POST",
                config.endpoint + "/api/v1/products/edit",
                headers={
                    "Authorization": "Bearer " + credentials.token.get_secret_value()
                },
                body=[
                    {
                        "id": int(publication.external_id),
                        "quantity_in_stock": quantity,
                        "presence": presence,
                        "in_stock": quantity > 0,
                    }
                ],
            )
        )
        diagnostic: dict[str, object] = {
            "event": "channels.prom.stock.response",
            "publication_id": str(publication.id),
            "external_id": publication.external_id,
            "http_status": 200,
            "target_processed": int(publication.external_id) in response.processed_ids,
            "processed_count": len(response.processed_ids),
            "error_count": len(response.errors),
            "warning_count": len(response.warnings),
        }
        provider_error = response.errors.get(publication.external_id, response.errors)
        code = provider_error.get("code") if isinstance(provider_error, dict) else None
        if type(code) is int or (
            isinstance(code, str)
            and re.fullmatch(r"[A-Za-z][A-Za-z0-9_.-]{0,63}", code)
            and credentials.token.get_secret_value() not in code
        ):
            diagnostic["provider_error_code"] = code
        logger.log(
            logging.WARNING if response.errors or response.warnings else logging.DEBUG,
            "Prom stock response: publication_id=%s external_id=%s processed=%s errors=%d warnings=%d provider_error_code=%s",
            publication.id,
            publication.external_id,
            diagnostic["target_processed"],
            diagnostic["error_count"],
            diagnostic["warning_count"],
            diagnostic.get("provider_error_code"),
            extra=diagnostic,
        )
        if response.errors:
            raise VerificationFailure("stock_write_rejected")
        result = await self.get(
            config=config, credentials=credentials, publication=publication
        )
        expected_availability = {
            "available": "in_stock",
            "not_available": "out_of_stock",
            "order": "on_order",
        }[presence]
        if (
            result.stock.mode != "own"
            or result.stock.quantity != quantity
            or result.stock.availability != expected_availability
        ):
            logger.warning(
                "Prom stock unconfirmed: publication_id=%s external_id=%s",
                publication.id,
                publication.external_id,
                extra={
                    "event": "channels.prom.stock.unconfirmed",
                    "publication_id": str(publication.id),
                    "external_id": publication.external_id,
                    "expected_quantity": quantity,
                    "observed_quantity": (
                        str(result.stock.quantity)
                        if result.stock.quantity is not None
                        else None
                    ),
                    "expected_availability": expected_availability,
                    "observed_availability": result.stock.availability,
                    "observed_mode": result.stock.mode,
                },
            )
            raise VerificationFailure("stock_write_unconfirmed", retryable=True)
        return result
