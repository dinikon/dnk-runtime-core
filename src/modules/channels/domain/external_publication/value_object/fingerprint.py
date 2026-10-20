from datetime import datetime, timezone
from hashlib import sha256
import json
from src.modules.channels.domain.external_publication.value_object.payload import (
    PublicationPayloadVO,
)
from src.modules.channels.domain.external_publication.value_object.meta import (
    PublicationMetaVO,
)


def publication_fingerprint(
    payload: PublicationPayloadVO,
    meta: PublicationMetaVO,
    source_updated_at: datetime | None,
) -> str:
    """Хеширует нормализованные данные независимо от порядка JSON и масштаба Decimal."""
    return sha256(
        json.dumps(
            {
                "payload": payload.to_document(),
                "meta": meta.to_document(),
                "source_updated_at": (
                    source_updated_at.astimezone(timezone.utc).isoformat()
                    if source_updated_at is not None
                    else None
                ),
            },
            sort_keys=True,
            ensure_ascii=False,
            allow_nan=False,
        ).encode()
    ).hexdigest()
