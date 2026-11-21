from dataclasses import dataclass
from datetime import datetime
from typing import Self
from src.modules.feed_builder.domain.feed.enum.export_format import ExportFormat
from src.modules.feed_builder.domain.generation.error import InvalidGenerationValueError
from src.modules.feed_builder.domain.generation.value_object.artifact_checksum import (
    ArtifactChecksumVO,
)
from src.modules.feed_builder.domain.generation.value_object.artifact_content_type import (
    ArtifactContentTypeVO,
)
from src.modules.feed_builder.domain.generation.value_object.artifact_storage_key import (
    ArtifactStorageKeyVO,
)
from src.modules.feed_builder.domain.generation.value_object.feed_artifact_id import (
    FeedArtifactIdVO,
)
from src.modules.feed_builder.domain.validation import require_datetime, require_integer


@dataclass(frozen=True, slots=True)
class FeedArtifact:
    """Зависимая Entity единственного итогового файла генерации."""

    id: FeedArtifactIdVO
    format: ExportFormat
    storage_key: ArtifactStorageKeyVO
    content_type: ArtifactContentTypeVO
    checksum: ArtifactChecksumVO
    size_bytes: int
    created_at: datetime

    @classmethod
    def create(
        cls,
        *,
        identifier: FeedArtifactIdVO,
        format: ExportFormat,
        storage_key: ArtifactStorageKeyVO,
        content_type: ArtifactContentTypeVO,
        checksum: ArtifactChecksumVO,
        size_bytes: int,
        now: datetime,
    ) -> Self:
        """Создаёт метаданные готового файла, не обращаясь к storage."""
        return cls.restore(
            identifier=identifier,
            format=format,
            storage_key=storage_key,
            content_type=content_type,
            checksum=checksum,
            size_bytes=size_bytes,
            created_at=now,
        )

    @classmethod
    def restore(
        cls,
        *,
        identifier: FeedArtifactIdVO,
        format: ExportFormat,
        storage_key: ArtifactStorageKeyVO,
        content_type: ArtifactContentTypeVO,
        checksum: ArtifactChecksumVO,
        size_bytes: int,
        created_at: datetime,
    ) -> Self:
        """Проверяет метаданные и соответствие базового MIME-типа формату."""
        if (
            not isinstance(identifier, FeedArtifactIdVO)
            or not isinstance(format, ExportFormat)
            or not isinstance(storage_key, ArtifactStorageKeyVO)
            or not isinstance(content_type, ArtifactContentTypeVO)
            or not isinstance(checksum, ArtifactChecksumVO)
        ):
            raise InvalidGenerationValueError("Нужны типизированные метаданные файла.")
        require_integer(size_bytes, minimum=0, error=InvalidGenerationValueError)
        require_datetime(created_at, error=InvalidGenerationValueError)
        expected_type = "text/csv" if format is ExportFormat.CSV else "application/xml"
        if content_type.value != expected_type:
            raise InvalidGenerationValueError(
                "MIME-тип не соответствует формату файла."
            )
        return cls(
            id=identifier,
            format=format,
            storage_key=storage_key,
            content_type=content_type,
            checksum=checksum,
            size_bytes=size_bytes,
            created_at=created_at,
        )
