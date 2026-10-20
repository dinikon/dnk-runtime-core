from dataclasses import asdict
from src.modules.channels.domain.external_publication.value_object.core import (
    PublicationCoreVO,
)
from src.modules.channels.domain.external_publication.value_object.payload import (
    PublicationPayloadVO,
)
from src.modules.channels.domain.external_publication.value_object.meta import (
    PublicationMetaVO,
)
from src.modules.channels.infrastructure.plugin.prom.promotion import promotion_period
from src.modules.channels.infrastructure.plugin.prom.manifest import PromSettings
from datetime import date
from src.modules.channels.application.plugin_contract import (
    ProviderJsonValue,
    ResourceSettingsDTO,
    PublicationCoreDTO,
    ObservedPublicationDTO,
)
from src.modules.channels.infrastructure.plugin.core_normalizer import (
    optional_decimal,
    safe_text,
    safe_url,
    currency_code,
    native_id,
    clean_description,
)
from src.modules.channels.infrastructure.plugin.prom.publication_read_schema import (
    PromReadExtension,
)
from src.modules.channels.infrastructure.plugin.prom.sale_price import (
    normalize_sale_price,
)
from src.modules.channels.infrastructure.plugin.prom.translations import localized_field
from src.modules.channels.infrastructure.plugin.prom.images import original_image_url


def normalize_product(
    row: dict[str, ProviderJsonValue],
    settings: ResourceSettingsDTO,
    *,
    observed_on: date,
) -> ObservedPublicationDTO:
    """Нормализует цену, действующую скидку и остаток на дату наблюдения Prom."""
    parsed = PromSettings.model_validate(settings.options)
    identifier = native_id(row.get("id"))
    warnings: list[str] = []
    raw_quantity = row.get("quantity_in_stock")
    if raw_quantity is None or raw_quantity == "":
        warnings.append("quantity_not_exposed")
    quantity = optional_decimal(raw_quantity, warnings, "quantity")
    price = optional_decimal(row.get("price"), warnings, "price")
    discount = row.get("discount")
    sale_price = normalize_sale_price(price, discount, observed_on, warnings)
    safe_discount = None
    if isinstance(discount, dict):
        safe_discount = {
            key: str(discount[key])[:100] if discount.get(key) is not None else None
            for key in ("value", "type", "date_start", "date_end")
        }
    title = safe_text(
        localized_field(row, "name", parsed.locales[0]), 2000, warnings, "title"
    )
    if not title:
        warnings.append("title_missing")
    currency = currency_code(row.get("currency"), warnings)
    group = row.get("group")
    extension = PromReadExtension(
        status=safe_text(row.get("status"), 100, warnings, "status"),
        group_id=(
            group.get("id")
            if isinstance(group, dict) and isinstance(group.get("id"), int)
            else None
        ),
        import_key=safe_text(
            row.get("external_id"), 512, warnings, "provider_external_id"
        ),
        description=clean_description(
            localized_field(row, "description", parsed.locales[0])
        ),
        discount=safe_discount,
    )
    titles = tuple(
        (locale, value)
        for locale in parsed.locales
        if (
            value := safe_text(
                localized_field(row, "name", locale), 2000, warnings, "title"
            )
        )
        is not None
    )
    core = PublicationCoreDTO(
        "product",
        identifier,
        safe_text(row.get("sku"), 512, warnings, "external_sku"),
        price,
        sale_price,
        currency,
        quantity,
        {
            "available": "in_stock",
            "not_available": "out_of_stock",
            "order": "on_backorder",
            "waiting": "on_backorder",
        }.get(
            row.get("presence") if isinstance(row.get("presence"), str) else "",
            "unknown",
        ),
        title,
        parsed.locales[0],
        safe_url(original_image_url(row.get("main_image")), warnings),
        None,
        tuple(warnings),
    )
    return ObservedPublicationDTO(
        core.resource_type,
        core.external_id,
        PublicationPayloadVO.from_core(
            PublicationCoreVO(**asdict(core)),
            promotion=promotion_period(extension),
            titles=titles,
        ),
        PublicationMetaVO.create(
            "prom.read.v2", extension.model_dump(mode="json"), tuple(warnings)
        ),
        core.source_updated_at,
    )
