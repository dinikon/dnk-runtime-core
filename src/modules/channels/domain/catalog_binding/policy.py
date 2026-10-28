from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.channels.domain.catalog_binding.entity import CatalogBindingItem
from src.modules.channels.domain.catalog_binding.value_object import (
    BindingAssessment,
    BindingClaim,
    BindingMode,
    CatalogFamily,
    PublicationNode,
)


class BindingStructurePolicy:
    """Одна политика для записи и вычисляемого read-side состояния."""

    def assess(
        self,
        *,
        mode: BindingMode,
        catalog_root_id: EntityIdVO,
        catalog: CatalogFamily | None,
        publication_root_id: EntityIdVO | None,
        items: tuple[CatalogBindingItem, ...],
        nodes: tuple[PublicationNode, ...],
        claims: tuple[BindingClaim, ...],
        platform: str,
        group_id: EntityIdVO | None = None,
    ) -> BindingAssessment:
        """Разрешает частичные пары, запрещая смешение семейств и чужое закрепление."""
        issues: list[str] = []
        by_id = {v.id: v for v in nodes}
        catalog_ids = set(catalog.positions) if catalog else set()
        if catalog is None or catalog.id != catalog_root_id:
            issues.append("binding_catalog_missing")
        elif catalog.kind != (
            "simple" if mode is BindingMode.SIMPLE_TO_SIMPLE else "variable"
        ):
            issues.append("binding_catalog_kind_invalid")
        if len({v.catalog_position_id for v in items}) != len(items) or len(
            {v.publication_id for v in items}
        ) != len(items):
            issues.append("binding_position_duplicate")
        if any(v.catalog_position_id not in catalog_ids for v in items):
            issues.append("binding_catalog_position_invalid")
        if not items:
            issues.append("binding_items_empty")
        source_ids: set[EntityIdVO] = set()
        reserved: set[EntityIdVO] = set()
        if mode is BindingMode.VARIABLE_TO_SIMPLE:
            if publication_root_id is not None:
                issues.append("binding_root_invalid")
            source_ids = {v.publication_id for v in items}
            reserved = set(source_ids)
            for identifier in source_ids:
                node = by_id.get(identifier)
                if (
                    node is None
                    or node.kind != "simple"
                    or node.parent_id is not None
                    or any(v.parent_id == identifier for v in nodes)
                ):
                    issues.append("binding_publication_not_standalone")
        else:
            root = by_id.get(publication_root_id)
            children = (
                tuple(v for v in nodes if v.parent_id == publication_root_id)
                if publication_root_id
                else ()
            )
            if root is None or root.parent_id is not None:
                issues.append("binding_publication_root_invalid")
            if mode is BindingMode.SIMPLE_TO_SIMPLE:
                if root is None or root.kind != "simple" or children:
                    issues.append("binding_simple_structure_invalid")
                source_ids = {root.id} if root else set()
            else:
                required = {"prom": "simple", "woocommerce": "variable"}.get(platform)
                if (
                    required is None
                    or root is None
                    or root.kind != required
                    or not children
                ):
                    issues.append("binding_variable_structure_invalid")
                source_ids = {v.id for v in children}
                if root and platform == "prom":
                    source_ids.add(root.id)
                if any(v.kind != "variant" for v in children):
                    issues.append("binding_variable_structure_invalid")
            reserved = source_ids | ({root.id} if root else set())
            if any(v.publication_id not in source_ids for v in items):
                issues.append("binding_publication_position_invalid")
        # A standalone position may have become a child of a reserved family.
        for identifier in tuple(reserved):
            node = by_id.get(identifier)
            if node and node.parent_id:
                reserved.add(node.parent_id)
        if any(v.group_id != group_id and v.publication_id in reserved for v in claims):
            issues.append("binding_publication_occupied")
        structural = tuple(
            dict.fromkeys(v for v in issues if v != "binding_items_empty")
        )
        complete = bool(items) and len(items) == len(catalog_ids) == len(source_ids)
        state = "conflict" if structural else "linked" if complete else "partial"
        return BindingAssessment(
            state,
            tuple(dict.fromkeys(issues)),
            len(catalog_ids),
            len(source_ids),
            len(items),
        )
