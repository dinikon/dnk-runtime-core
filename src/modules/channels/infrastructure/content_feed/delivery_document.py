import json
from typing import cast

from pydantic import TypeAdapter, ValidationError

from src.modules.channels.domain.content_feed.delivery import FeedDeliveryVO
from src.modules.channels.domain.content_feed.error import ContentFeedError
from src.modules.channels.domain.types import JsonObject

DELIVERY_SCHEMA = "content_feed_delivery.v1"
_delivery = TypeAdapter(FeedDeliveryVO)


def decode_delivery(schema: str, value: JsonObject) -> FeedDeliveryVO:
    """Читает конкретную версию документа без исправления повреждённых записей."""
    if schema != DELIVERY_SCHEMA:
        raise ContentFeedError("feed_delivery_schema_unsupported")
    try:
        return _delivery.validate_json(json.dumps(value), strict=True)
    except (ValidationError, ValueError, TypeError):
        raise ContentFeedError("feed_delivery_invalid") from None


def encode_delivery(value: FeedDeliveryVO) -> JsonObject:
    """Сериализует только состояние доставки; секретный запрос хранится отдельно."""
    return cast(JsonObject, _delivery.dump_python(value, mode="json"))
