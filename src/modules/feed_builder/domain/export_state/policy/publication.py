from src.modules.feed_builder.domain.export_state.value_object.export_counts import (
    ExportCountsVO,
)
from src.modules.feed_builder.domain.feed.enum.validation_policy import ValidationPolicy


def publication_rejection_reason(
    policy: ValidationPolicy, counts: ExportCountsVO
) -> str | None:
    """Возвращает причину отклонения готового файла по итогам полной проверки."""
    if counts.rejected_items == 0:
        return None
    if policy is ValidationPolicy.STRICT:
        return "STRICT_REJECTED"
    if counts.valid_items + counts.warning_items == 0:
        return "ALL_ITEMS_REJECTED"
    return None
