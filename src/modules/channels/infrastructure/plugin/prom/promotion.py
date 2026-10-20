from datetime import datetime
from src.modules.channels.domain.external_publication.value_object.payload import (
    PublicationPromotionVO,
)
from src.modules.channels.infrastructure.plugin.prom.publication_read_schema import (
    PromReadExtension,
)


def promotion_period(metadata: PromReadExtension) -> PublicationPromotionVO | None:
    """Нормализует календарные границы; исходные значения остаются в meta."""
    discount = metadata.discount
    if not discount:
        return None
    try:
        dates = tuple(
            (
                datetime.strptime(discount[key], "%d.%m.%Y").date().isoformat()
                if discount.get(key)
                else None
            )
            for key in ("date_start", "date_end")
        )
    except (ValueError, TypeError):
        return None
    if not any(dates) or (all(dates) and dates[0] > dates[1]):
        return None
    return PublicationPromotionVO(*dates, "Europe/Kyiv", "day")
