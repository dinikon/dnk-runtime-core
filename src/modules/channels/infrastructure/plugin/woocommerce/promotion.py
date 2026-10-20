from datetime import datetime, timezone
from src.modules.channels.domain.external_publication.value_object.payload import (
    PublicationPromotionVO,
)
from src.modules.channels.infrastructure.plugin.woocommerce.publication_read_schema import (
    WooReadExtension,
)


def promotion_period(metadata: WooReadExtension) -> PublicationPromotionVO | None:
    """Читает GMT-границы акции, не подменяя ими текущую цену источника."""
    try:
        dates = tuple(
            (
                datetime.fromisoformat(value).replace(tzinfo=timezone.utc).isoformat()
                if value
                else None
            )
            for value in (metadata.sale_start_gmt, metadata.sale_end_gmt)
        )
    except (ValueError, TypeError):
        return None
    if not any(dates) or (all(dates) and dates[0] > dates[1]):
        return None
    return PublicationPromotionVO(*dates, "UTC", "instant")
