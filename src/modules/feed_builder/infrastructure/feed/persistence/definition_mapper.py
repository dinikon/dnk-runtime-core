from src.modules.feed_builder.application.feed.schema_definition import (
    decode_schema as schema_from_document,
)
from src.modules.feed_builder.application.feed.schema_error import (
    InvalidFeedSchemaDocumentError,
)
from src.modules.feed_builder.domain.feed.value_object.feed_schema import FeedSchemaVO
from src.modules.feed_builder.infrastructure.feed.persistence.error import (
    InvalidFeedStorageError,
)
from src.modules.shared.domain.domain_error import DomainError


def decode_schema(value: object) -> FeedSchemaVO:
    """Восстанавливает сохранённое определение, отличая повреждение БД от входных ошибок."""
    try:
        return schema_from_document(value)
    except (InvalidFeedSchemaDocumentError, DomainError) as exc:
        raise InvalidFeedStorageError(
            "Некорректное сохранённое определение Feed."
        ) from exc
