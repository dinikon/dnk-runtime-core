from datetime import datetime
from dataclasses import asdict
from decimal import Decimal
from src.modules.channels.application.plugin_contract import (
    ReadPublicationDetailsOutcomeDTO,
)
from src.modules.channels.application.product_representation.contracts import (
    CatalogDraftValuesDTO,
)
from src.modules.channels.domain.publication_import.value_object.snapshot import (
    ImportSnapshotVO,
    ImportImageVO,
)
from src.modules.channels.domain.error import ChannelsValidationError


def snapshot_for_import(
    outcome: ReadPublicationDetailsOutcomeDTO,
    locales: tuple[str, ...],
    read_at: datetime | None = None,
) -> ImportSnapshotVO:
    """Закрепляет нормализованное содержимое, не читая технический extensions."""
    if tuple(t.locale for t in outcome.translations) != locales:
        raise ChannelsValidationError("publication_locales_mismatch")
    core = outcome.core
    titles = {t.locale: t.title or "" for t in outcome.translations}
    quantified = core.quantity is not None
    values = CatalogDraftValuesDTO(
        titles,
        core.external_sku,
        core.price,
        core.sale_price,
        core.currency if core.price is not None else None,
        quantified,
        core.quantity,
        None if quantified or core.stock_status == "unknown" else core.stock_status,
        "no",
    )
    primitive = asdict(values)
    for key in ("regular_price", "sale_price", "quantity"):
        primitive[key] = str(primitive[key]) if primitive[key] is not None else None
    primitive.pop("image_files", None)
    return ImportSnapshotVO(
        {t.locale: {"title": t.title, "body": t.body} for t in outcome.translations},
        tuple(ImportImageVO(i.id, i.url, i.alt) for i in outcome.images),
        primitive,
        tuple(dict.fromkeys((*core.warnings, *outcome.warnings))),
        read_at,
        core.source_updated_at,
    )
