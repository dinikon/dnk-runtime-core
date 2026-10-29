from src.modules.channels.domain.catalog_binding.value_object import PublicationNode
from src.modules.channels.domain.external_publication.error import (
    InvalidExternalPublicationError,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


class PublicationCatalogPolicy:
    """Сохраняет один канонический контейнер вариативной публикации."""

    def kind(
        self, *, platform: str, root_id: EntityIdVO, nodes: tuple[PublicationNode, ...]
    ) -> str:
        """Разрешает самостоятельную Simple либо поддержанное нативное семейство."""
        root = next((n for n in nodes if n.id == root_id), None)
        children = tuple(n for n in nodes if n.id != root_id)
        if (
            root is None
            or root.parent_id is not None
            or any(n.kind != "variant" or n.parent_id != root_id for n in children)
        ):
            raise InvalidExternalPublicationError("Некорректная структура публикации.")
        if root.kind == "simple" and not children:
            return "simple"
        if children and (
            (platform == "prom" and root.kind == "simple")
            or (platform == "woocommerce" and root.kind == "variable")
        ):
            return "variable"
        raise InvalidExternalPublicationError(
            "Сначала синхронизируйте состав вариантов публикации."
        )

    def ensure_same_source(
        self,
        *,
        expected: tuple[tuple[str, str, str, str | None], ...],
        actual: tuple[tuple[str, str, str, str | None], ...],
    ) -> None:
        """Не разрешает создавать связи с изменившимися ролями или составом источника."""
        if len(actual) != len(expected) or set(actual) != set(expected):
            raise InvalidExternalPublicationError(
                "Сначала синхронизируйте состав публикации."
            )
