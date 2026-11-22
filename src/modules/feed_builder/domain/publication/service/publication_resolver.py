from dataclasses import dataclass
from uuid import UUID

from src.modules.feed_builder.domain.feed.value_object.feed_schema import FeedSchemaVO
from src.modules.feed_builder.domain.publication.service.field_value_resolver import (
    FieldIssue,
    FieldValueResolver,
    ResolvedField,
)
from src.modules.feed_builder.domain.publication.value_object.field_override import (
    FieldOverrideVO,
)
from src.modules.feed_builder.domain.publication.value_object.publication_catalog_snapshot import (
    PublicationCatalogSnapshotVO,
)


@dataclass(frozen=True, slots=True)
class ResolvedPublication:
    """Содержит готовые значения в порядке схемы и ошибки конкретной публикации."""

    publication_id: UUID
    fields: tuple[ResolvedField, ...]
    issues: tuple[FieldIssue, ...]
    readiness: str


class PublicationResolver:
    """Разрешает все поля публикации по одному неизменяемому снимку."""

    def resolve(
        self,
        publication_id: UUID,
        schema: FeedSchemaVO,
        overrides: tuple[FieldOverrideVO, ...],
        snapshot: PublicationCatalogSnapshotVO | None,
    ) -> ResolvedPublication:
        """Сохраняет порядок схемы и отделяет ошибку позиции от ошибок полей."""
        if snapshot is None:
            return ResolvedPublication(
                publication_id,
                (),
                (
                    FieldIssue(
                        None,
                        "SOURCE_UNAVAILABLE",
                        "Выбранная позиция Catalog недоступна.",
                    ),
                ),
                "INVALID",
            )
        by_field = {override.field_id: override for override in overrides}
        resolver = FieldValueResolver()
        fields = tuple(
            resolver.resolve(field, snapshot, by_field.get(field.id))
            for field in schema.fields
        )
        issues = tuple(issue for field in fields for issue in field.issues)
        if any(issue.code != "REQUIRED_VALUE_MISSING" for issue in issues):
            readiness = "INVALID"
        else:
            readiness = "NEEDS_INPUT" if issues else "READY"
        return ResolvedPublication(publication_id, fields, issues, readiness)
