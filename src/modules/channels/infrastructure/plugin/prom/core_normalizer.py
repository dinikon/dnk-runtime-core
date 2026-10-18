from src.modules.channels.application.plugin_contract import (
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
from src.modules.channels.domain.external_publication.value_object.core import JsonValue


def normalize_product(
    row: dict[str, JsonValue], settings: ResourceSettingsDTO
) -> ObservedPublicationDTO:
    """Различает native ID и import external_id; неизвестную скидку не вычисляет."""
    identifier = native_id(row.get("id"))
    warnings: list[str] = []
    raw_quantity = row.get("quantity_in_stock")
    if raw_quantity is None or raw_quantity == "":
        warnings.append("quantity_not_exposed")
    quantity = optional_decimal(raw_quantity, warnings, "quantity")
    price = optional_decimal(row.get("price"), warnings, "price")
    discount = row.get("discount")
    safe_discount = None
    if isinstance(discount, dict):
        warnings.append("sale_price_semantics_unverified")
        safe_discount = {
            key: str(discount[key])[:100] if discount.get(key) is not None else None
            for key in ("value", "type", "date_start", "date_end")
        }
    title = safe_text(row.get("name"), 2000, warnings, "title")
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
        provider_external_id=safe_text(
            row.get("external_id"), 512, warnings, "provider_external_id"
        ),
        description=clean_description(row.get("description")),
        discount=safe_discount,
    )
    core = PublicationCoreDTO(
        "product",
        identifier,
        safe_text(row.get("sku"), 512, warnings, "external_sku"),
        price,
        None,
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
        settings.locales[0],
        safe_url(row.get("main_image"), warnings),
        None,
        tuple(warnings),
    )
    return ObservedPublicationDTO(
        core, "prom.read.v1", extension.model_dump(mode="json")
    )
