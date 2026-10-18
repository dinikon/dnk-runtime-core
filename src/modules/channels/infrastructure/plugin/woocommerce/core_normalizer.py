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
    observed_time,
)
from src.modules.channels.infrastructure.plugin.woocommerce.publication_read_schema import (
    WooReadExtension,
)
from src.modules.channels.domain.external_publication.value_object.core import JsonValue


def normalize_product(
    row: dict[str, JsonValue],
    settings: ResourceSettingsDTO,
    parent_id: int | None = None,
) -> ObservedPublicationDTO:
    """Нормализует simple/variable/variation без создания товаров Catalog."""
    identifier = native_id(row.get("id"))
    warnings = []
    price = optional_decimal(row.get("regular_price"), warnings, "price")
    sale = optional_decimal(row.get("sale_price"), warnings, "sale_price")
    if price is not None and sale is not None and (sale > price):
        warnings.append("sale_price_exceeds_regular")
    quantity = optional_decimal(row.get("stock_quantity"), warnings, "quantity")
    image = row.get("image")
    if not isinstance(image, dict):
        images = row.get("images")
        image = (
            images[0]
            if isinstance(images, list) and images and isinstance(images[0], dict)
            else {}
        )
    title = safe_text(row.get("name"), 2000, warnings, "title")
    if not title:
        warnings.append("title_missing")
    extension = WooReadExtension(
        parent_id=parent_id,
        product_type=safe_text(row.get("type"), 100, warnings, "product_type"),
        status=safe_text(row.get("status"), 100, warnings, "status"),
        description=clean_description(row.get("description")),
        sale_start_gmt=safe_text(
            row.get("date_on_sale_from_gmt"), 100, warnings, "sale_start"
        ),
        sale_end_gmt=safe_text(
            row.get("date_on_sale_to_gmt"), 100, warnings, "sale_end"
        ),
    )
    core = PublicationCoreDTO(
        "variation" if parent_id else "product",
        identifier,
        safe_text(row.get("sku"), 512, warnings, "external_sku"),
        price,
        sale,
        currency_code(settings.currency, warnings),
        quantity,
        {
            "instock": "in_stock",
            "outofstock": "out_of_stock",
            "onbackorder": "on_backorder",
        }.get(
            row.get("stock_status") if isinstance(row.get("stock_status"), str) else "",
            "unknown",
        ),
        title,
        settings.locales[0],
        safe_url(image.get("src"), warnings),
        observed_time(row.get("date_modified_gmt"), warnings, utc_field=True),
        tuple(warnings),
    )
    return ObservedPublicationDTO(
        core, "woocommerce.read.v1", extension.model_dump(mode="json")
    )
