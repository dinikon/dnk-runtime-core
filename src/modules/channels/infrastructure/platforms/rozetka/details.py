from urllib.parse import urlencode
from pydantic import BaseModel, field_validator
from src.modules.channels.infrastructure.platforms.rozetka.publications import (
    RozetkaPublication,
    RozetkaPublicationReader,
)
from src.modules.channels.infrastructure.platforms.rozetka.models import (
    RozetkaConfig,
    RozetkaCredentials,
)
from src.modules.channels.infrastructure.http import JsonHttp
from src.modules.channels.application.error import VerificationFailure
from src.modules.channels.application.external_publication.catalog_details import (
    PublicationLookup,
    PublicationDetails,
    PublicationProductDetails,
    PublicationTranslationDetails,
)


class RozetkaProductDetails(RozetkaPublication):
    """В details поле description относится к русскому, description_ua — к украинскому."""

    description: str | None = None
    description_ua: str | None = None

    @field_validator("photo_preview", mode="before")
    @classmethod
    def photo_preview_urls(cls, value: object) -> object:
        """Details возвращает превью строкой либо массивом; пустая строка означает отсутствие."""
        if isinstance(value, str):
            return [value] if value else []
        return value


class RozetkaDetailContent(BaseModel):
    """Поддерживает документированный массив item и одиночный объект ответа."""

    item: RozetkaProductDetails | list[RozetkaProductDetails]


class RozetkaDetailResponse(BaseModel):
    """HTTP 200 не заменяет проверку success."""

    success: bool
    content: RozetkaDetailContent | None = None


class RozetkaDetailsReader:
    """Читает официальный GET /goods/details по внутреннему или marketplace ID."""

    def __init__(self, http: JsonHttp) -> None:
        """Получает общий transport с токенной авторизацией."""
        self.http = http

    async def read(
        self,
        *,
        config: RozetkaConfig,
        credentials: RozetkaCredentials,
        publications: tuple[PublicationLookup, ...],
    ) -> PublicationDetails:
        """Сверяет стабильный ключ прайса, не подменяя его rz_item_id."""
        root = next(p for p in publications if p.parent_id is None)
        native_ids = root.platform_data
        item_id, rz_item_id = native_ids.get("item_id"), native_ids.get("rz_item_id")
        params = (
            {"item_id": item_id}
            if type(item_id) is int and item_id > 0
            else (
                {"rz_item_id": rz_item_id}
                if type(rz_item_id) is int and rz_item_id > 0
                else None
            )
        )
        if params is None:
            raise VerificationFailure("publication_details_unavailable")
        if type(native_ids.get("sync_source_id")) is int:
            params["sync_source_id"] = native_ids["sync_source_id"]
        response = RozetkaDetailResponse.model_validate(
            await self.http.request(
                "GET",
                config.endpoint + "/goods/details?" + urlencode(params),
                headers={
                    "Authorization": "Bearer " + credentials.token.get_secret_value()
                },
            )
        )
        if not response.success or response.content is None:
            raise VerificationFailure("provider_response_invalid")
        records = (
            response.content.item
            if isinstance(response.content.item, list)
            else [response.content.item]
        )
        if len(records) != 1:
            raise VerificationFailure("publication_identity_invalid")
        native = records[0]
        observation = RozetkaPublicationReader(self.http).normalize(
            native.model_dump(mode="json"), config
        )
        if observation.external_id != root.external_id:
            raise VerificationFailure("publication_identity_invalid")
        data = observation.data
        tracked = data.quantity is not None
        status = {
            "in_stock": "in_stock",
            "out_of_stock": "out_of_stock",
            "removed": "out_of_stock",
        }.get(data.availability)
        warnings: list[str] = []
        regular_price = data.price
        if data.regular_price is not None and (
            regular_price is None or data.regular_price > regular_price
        ):
            regular_price = data.regular_price
        elif (
            data.regular_price is not None
            and data.price is not None
            and data.regular_price < data.price
        ):
            warnings.append(
                "Старая цена Rozetka ниже текущей и не использована как обычная цена."
            )
        sale_price = (
            data.price
            if data.price is not None
            and regular_price is not None
            and data.price < regular_price
            else None
        )
        if data.sale_price is not None and regular_price is not None:
            current_price = sale_price if sale_price is not None else regular_price
            if data.sale_price < current_price:
                sale_price = data.sale_price
            elif data.sale_price > current_price:
                warnings.append(
                    "Промо-цена Rozetka выше текущей и не использована как акционная цена."
                )
        return PublicationDetails(
            (
                PublicationProductDetails(
                    "source_offer",
                    root.external_id,
                    None,
                    "simple",
                    native.article or None,
                    (
                        PublicationTranslationDetails(
                            "uk", native.name_ua, native.description_ua
                        ),
                        PublicationTranslationDetails(
                            "ru", native.name_ru, native.description
                        ),
                    ),
                    tuple(native.photo or native.photo_preview),
                    tracked,
                    data.quantity if tracked else None,
                    None if tracked else status,
                    regular_price=regular_price,
                    currency=config.settings.currency,
                    sale_price=sale_price,
                ),
            ),
            tuple(warnings),
        )
