from src.modules.channels.domain.catalog_binding.entity import CatalogBindingItem
from src.modules.channels.domain.catalog_binding.policy import BindingStructurePolicy
from src.modules.channels.domain.catalog_binding.value_object import (
    BindingClaim,
    BindingMode,
    CatalogFamily,
)
from src.modules.channels.domain.product_representation.value_object import (
    CatalogContentSnapshot,
    ContentTargetRole,
    PreparedPublicationContent,
    PublicationContentSnapshot,
    RepresentationIssue,
    RepresentationPreparation,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


class RepresentationPolicy:
    """Формирует контент целей по действующей структуре сопоставления."""

    def prepare(
        self,
        *,
        group_id: EntityIdVO,
        platform: str,
        mode: BindingMode,
        catalog_root_id: EntityIdVO,
        catalog_root: CatalogContentSnapshot | None,
        catalog_positions: tuple[CatalogContentSnapshot, ...],
        publication_root_id: EntityIdVO | None,
        items: tuple[CatalogBindingItem, ...],
        publications: tuple[PublicationContentSnapshot, ...],
        claims: tuple[BindingClaim, ...],
    ) -> RepresentationPreparation:
        """Не скрывает конфликтные пары; общий Woo-контейнер требует полной семьи."""
        assessment = BindingStructurePolicy().assess(
            group_id=group_id,
            platform=platform,
            mode=mode,
            catalog_root_id=catalog_root_id,
            catalog=(
                CatalogFamily(
                    catalog_root.id,
                    catalog_root.kind,
                    tuple(value.id for value in catalog_positions),
                )
                if catalog_root
                else None
            ),
            publication_root_id=publication_root_id,
            items=items,
            nodes=tuple(value.structure for value in publications),
            claims=claims,
        )
        issues = tuple(RepresentationIssue(code) for code in assessment.issues)
        by_id = {value.structure.id: value for value in publications}
        catalog = {value.id: value for value in catalog_positions}
        targets: list[PreparedPublicationContent] = []
        if (
            mode is BindingMode.VARIABLE_TO_VARIABLE
            and platform == "woocommerce"
            and publication_root_id is not None
        ):
            blockers = issues
            if assessment.state == "partial":
                blockers += (RepresentationIssue("representation_family_incomplete"),)
            if any(value.stale for value in publications):
                blockers += (RepresentationIssue("representation_publication_stale"),)
            targets.append(
                self._target(
                    publication_id=publication_root_id,
                    publication=by_id.get(publication_root_id),
                    catalog_position_id=catalog_root_id,
                    catalog=catalog_root,
                    binding_item_id=None,
                    role=ContentTargetRole.CONTAINER,
                    issues=blockers,
                )
            )
        for item in items:
            publication = by_id.get(item.publication_id)
            blockers = issues
            parent = by_id.get(publication.structure.parent_id) if publication else None
            if (publication and publication.stale) or (parent and parent.stale):
                blockers += (RepresentationIssue("representation_publication_stale"),)
            targets.append(
                self._target(
                    publication_id=item.publication_id,
                    publication=publication,
                    catalog_position_id=item.catalog_position_id,
                    catalog=catalog.get(item.catalog_position_id),
                    binding_item_id=item.id,
                    role=ContentTargetRole.POSITION,
                    issues=blockers,
                )
            )
        return RepresentationPreparation(assessment, tuple(targets), issues)

    @staticmethod
    def _target(
        *,
        publication_id: EntityIdVO,
        publication: PublicationContentSnapshot | None,
        catalog_position_id: EntityIdVO,
        catalog: CatalogContentSnapshot | None,
        binding_item_id: EntityIdVO | None,
        role: ContentTargetRole,
        issues: tuple[RepresentationIssue, ...],
    ) -> PreparedPublicationContent:
        """Оставляет отсутствующий контент отсутствующим, не подставляя данные площадки."""
        blockers = list(issues)
        if publication is None:
            blockers.append(
                RepresentationIssue(
                    "representation_publication_missing", publication_id
                )
            )
        elif not publication.external_id:
            blockers.append(
                RepresentationIssue(
                    "representation_external_id_missing", publication_id
                )
            )
        if catalog is None:
            blockers.append(
                RepresentationIssue("representation_catalog_missing", publication_id)
            )
        else:
            for value in catalog.content:
                if value.title is None or not value.title.strip():
                    blockers.append(
                        RepresentationIssue(
                            "representation_title_missing",
                            publication_id,
                            "title",
                            value.locale,
                        )
                    )
        return PreparedPublicationContent(
            publication_id=publication_id,
            external_id=publication.external_id if publication else None,
            parent_publication_id=(
                publication.structure.parent_id if publication else None
            ),
            publication_kind=publication.structure.kind if publication else None,
            binding_item_id=binding_item_id,
            catalog_position_id=catalog_position_id,
            role=role,
            content=catalog.content if catalog else (),
            issues=tuple(blockers),
        )
