from src.modules.feed_builder.domain.feed.field_node.category.value_object.data import (
    CategoryNodeDataVO,
)
from dataclasses import dataclass
from uuid import UUID

from src.modules.feed_builder.domain.feed.value_object.feed_schema import FeedSchemaVO
from src.modules.feed_builder.domain.publication.field_node.resolver import (
    NodeValueResolver,
)
from src.modules.feed_builder.domain.publication.field_node.result import (
    FieldIssue,
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


class PublicationNodeResolver:
    """Разрешает все поля публикации по одному неизменяемому снимку."""

    def __init__(self, resolver: NodeValueResolver | None = None) -> None:
        """Принимает диспетчер нод текущего сценария."""
        self._resolver = resolver if resolver is not None else NodeValueResolver()

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
        fields = tuple(
            self._resolver.resolve(field, snapshot, by_field.get(field.id))
            for field in schema.fields
            if not isinstance(field.type_definition, CategoryNodeDataVO)
        )
        issues = tuple(issue for field in fields for issue in field.issues)
        if any(issue.code != "REQUIRED_VALUE_MISSING" for issue in issues):
            readiness = "INVALID"
        else:
            readiness = "NEEDS_INPUT" if issues else "READY"
        return ResolvedPublication(publication_id, fields, issues, readiness)
