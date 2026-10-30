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
    LocalizedContent,
    ContentOrigins,
    ContentOrigin,
    FieldOrigin,
)
from src.modules.channels.domain.product_representation.overrides import (
    RepresentationOverridesVO,
    LocalizedOverridesVO,
)
from src.modules.channels.domain.product_representation.error import (
    ProductRepresentationError,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


from dataclasses import replace


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
        overrides: RepresentationOverridesVO = RepresentationOverridesVO(),
        unavailable_files: tuple[EntityIdVO, ...] = (),
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
                    overrides=overrides,
                    unavailable_files=unavailable_files,
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
                    overrides=overrides,
                    unavailable_files=unavailable_files,
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
        overrides: RepresentationOverridesVO,
        unavailable_files: tuple[EntityIdVO, ...],
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
        content: list[LocalizedContent] = []
        if catalog is not None:
            for value in catalog.content:
                value = RepresentationPolicy.apply_override(
                    content=value,
                    override=overrides.common_for(value.locale),
                    origin=ContentOrigin.GROUP_OVERRIDE,
                )
                if binding_item_id is not None:
                    value = RepresentationPolicy.apply_override(
                        content=value,
                        override=overrides.item_for(
                            binding_item_id=binding_item_id, locale=value.locale
                        ),
                        origin=ContentOrigin.ITEM_OVERRIDE,
                    )
                content.append(value)
                if any(
                    image.file_id in unavailable_files for image in value.gallery or ()
                ):
                    blockers.append(
                        RepresentationIssue(
                            "representation_image_unavailable",
                            publication_id,
                            "gallery",
                            value.locale,
                        )
                    )
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
            content=tuple(content),
            issues=tuple(blockers),
            catalog_content=catalog.content if catalog else (),
        )

    @staticmethod
    def with_unavailable_files(
        *, preparation: RepresentationPreparation, unavailable: tuple[EntityIdVO, ...]
    ) -> RepresentationPreparation:
        """Применяет факты Files ко всей эффективной галерее, включая Catalog."""
        targets = []
        for target in preparation.targets:
            issues = tuple(
                RepresentationIssue(
                    "representation_image_unavailable",
                    target.publication_id,
                    "gallery",
                    content.locale,
                )
                for content in target.content
                if any(image.file_id in unavailable for image in content.gallery or ())
            )
            targets.append(
                replace(target, issues=tuple(dict.fromkeys((*target.issues, *issues))))
            )
        return replace(preparation, targets=tuple(targets))

    @staticmethod
    def apply_override(
        *,
        content: LocalizedContent,
        override: LocalizedOverridesVO | None,
        origin: ContentOrigin,
    ) -> LocalizedContent:
        """Накладывает одно значение без потери пустой строки или галереи."""
        if override is None:
            return content
        source = FieldOrigin(origin, None)
        return LocalizedContent(
            locale=content.locale,
            title=override.title if override.title is not None else content.title,
            body=override.body if override.body is not None else content.body,
            gallery=(
                override.gallery if override.gallery is not None else content.gallery
            ),
            origins=ContentOrigins(
                source if override.title is not None else content.origins.title,
                source if override.body is not None else content.origins.body,
                source if override.gallery is not None else content.origins.gallery,
            ),
        )

    @staticmethod
    def ensure_overrides_scope(
        *,
        overrides: RepresentationOverridesVO,
        item_ids: tuple[EntityIdVO, ...],
        locales: tuple[str, ...],
        previous: RepresentationOverridesVO = RepresentationOverridesVO(),
    ) -> None:
        """Не допускает чужие пары и новые изменения неактивных локалей."""
        if any(item.binding_item_id not in item_ids for item in overrides.items):
            raise ProductRepresentationError("representation_item_not_in_group")
        for value in overrides.common:
            if value.locale not in locales and value != previous.common_for(
                value.locale
            ):
                raise ProductRepresentationError("representation_locale_inactive")
        for item in overrides.items:
            for value in item.content:
                if value.locale not in locales and value != previous.item_for(
                    binding_item_id=item.binding_item_id, locale=value.locale
                ):
                    raise ProductRepresentationError("representation_locale_inactive")

    @staticmethod
    def export_blockers(
        *,
        preparation: RepresentationPreparation,
        mode: BindingMode,
        verification_status: str,
        verification_revision: int,
        config_revision: int,
        has_identity: bool,
        unavailable_files: bool,
    ) -> tuple[str, ...]:
        """Отделяет пользовательское разрешение от текущей готовности к экспорту."""
        blockers: list[str] = []
        if (
            verification_status != "verified"
            or verification_revision != config_revision
            or not has_identity
        ):
            blockers.append("representation_connection_unverified")
        if (
            mode is BindingMode.VARIABLE_TO_VARIABLE
            and preparation.assessment.state != "linked"
        ):
            blockers.append("representation_family_incomplete")
        blockers.extend(issue.code for issue in preparation.issues)
        blockers.extend(
            issue.code for target in preparation.targets for issue in target.issues
        )
        if not preparation.targets:
            blockers.append("representation_targets_empty")
        if unavailable_files:
            blockers.append("representation_image_unavailable")
        return tuple(dict.fromkeys(blockers))
