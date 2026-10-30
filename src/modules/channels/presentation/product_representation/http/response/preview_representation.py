from datetime import datetime
from uuid import UUID

from pydantic import BaseModel
from src.modules.channels.presentation.product_representation.http.response.fields import (
    RepresentationStateResponse,
)

from src.modules.channels.application.product_representation.query.preview_representation.dto import (
    PreviewRepresentationResultDTO,
)
from src.modules.channels.domain.product_representation.value_object import (
    FieldOrigin,
    LocalizedContent,
    RepresentationIssue,
)


class PreviewFieldOriginResponse(BaseModel):
    """Показывает источник эффективного поля Catalog."""

    kind: str
    catalog_position_id: UUID | None

    @classmethod
    def from_origin(cls, value: FieldOrigin) -> "PreviewFieldOriginResponse":
        """Явно преобразует доменный идентификатор в публичный UUID."""
        return cls(
            kind=value.kind.value,
            catalog_position_id=(
                value.catalog_position_id.uuid if value.catalog_position_id else None
            ),
        )


class PreviewContentOriginsResponse(BaseModel):
    """Источники title/body/gallery выбранной локали."""

    title: PreviewFieldOriginResponse
    body: PreviewFieldOriginResponse
    gallery: PreviewFieldOriginResponse


class PreviewContentImageResponse(BaseModel):
    """Ссылка на Files; первое изображение является главным."""

    file_id: UUID
    alt: str
    caption: str


class PreviewLocalizedContentResponse(BaseModel):
    """Готовые значения одной локали с сохранением null и явной очистки."""

    locale: str
    title: str | None
    body: str | None
    gallery: tuple[PreviewContentImageResponse, ...] | None
    origins: PreviewContentOriginsResponse

    @classmethod
    def from_content(cls, value: LocalizedContent) -> "PreviewLocalizedContentResponse":
        """Перечисляет публичные поля, не сериализуя Domain автоматически."""
        return cls(
            locale=value.locale,
            title=value.title,
            body=value.body,
            gallery=(
                tuple(
                    PreviewContentImageResponse(
                        file_id=image.file_id.uuid, alt=image.alt, caption=image.caption
                    )
                    for image in value.gallery
                )
                if value.gallery is not None
                else None
            ),
            origins=PreviewContentOriginsResponse(
                title=PreviewFieldOriginResponse.from_origin(value.origins.title),
                body=PreviewFieldOriginResponse.from_origin(value.origins.body),
                gallery=PreviewFieldOriginResponse.from_origin(value.origins.gallery),
            ),
        )


class PreviewRepresentationIssueResponse(BaseModel):
    """Безопасный код причины с адресом цели, поля и локали."""

    code: str
    publication_id: UUID | None
    field: str | None
    locale: str | None

    @classmethod
    def from_issue(
        cls, value: RepresentationIssue
    ) -> "PreviewRepresentationIssueResponse":
        """Не включает технические исключения или исходные документы площадки."""
        return cls(
            code=value.code,
            publication_id=value.publication_id.uuid if value.publication_id else None,
            field=value.field,
            locale=value.locale,
        )


class PreviewPublicationContentResponse(BaseModel):
    """Итоговый контент контейнера или сопоставленной продаваемой позиции."""

    publication_id: UUID
    external_id: str | None
    parent_publication_id: UUID | None
    publication_kind: str | None
    binding_item_id: UUID | None
    catalog_position_id: UUID
    role: str
    content: tuple[PreviewLocalizedContentResponse, ...]
    ready: bool
    issues: tuple[PreviewRepresentationIssueResponse, ...]
    catalog_content: tuple[PreviewLocalizedContentResponse, ...] = ()


class PreviewPreparedRepresentationResponse(BaseModel):
    """Контекст одного согласованного preview без сохранённой копии Catalog."""

    channel_id: UUID
    connection_id: UUID
    binding_group_id: UUID
    binding_revision: int
    config_revision: int
    platform: str
    mode: str
    locales: tuple[str, ...]
    as_of: datetime
    binding_state: str
    issues: tuple[PreviewRepresentationIssueResponse, ...]
    targets: tuple[PreviewPublicationContentResponse, ...]


class PreviewRepresentationResponse(BaseModel):
    """Публичный контракт сценария preview_representation."""

    representation: PreviewPreparedRepresentationResponse
    state: RepresentationStateResponse
    export_blockers: tuple[str, ...]
    draft: bool

    @classmethod
    def from_dto(
        cls, result: PreviewRepresentationResultDTO
    ) -> "PreviewRepresentationResponse":
        """Явно выбирает поля результата; не раскрывает настройки и сырые наблюдения."""
        value = result.representation
        return cls(
            state=RepresentationStateResponse.from_state(result.state),
            export_blockers=result.export_blockers,
            draft=result.draft,
            representation=PreviewPreparedRepresentationResponse(
                channel_id=value.channel_id,
                connection_id=value.connection_id,
                binding_group_id=value.binding_group_id,
                binding_revision=value.binding_revision,
                config_revision=value.config_revision,
                platform=value.platform,
                mode=value.mode.value,
                locales=value.locales,
                as_of=value.as_of,
                binding_state=value.preparation.assessment.state,
                issues=tuple(
                    PreviewRepresentationIssueResponse.from_issue(issue)
                    for issue in value.preparation.issues
                ),
                targets=tuple(
                    PreviewPublicationContentResponse(
                        publication_id=target.publication_id.uuid,
                        external_id=target.external_id,
                        parent_publication_id=(
                            target.parent_publication_id.uuid
                            if target.parent_publication_id
                            else None
                        ),
                        publication_kind=target.publication_kind,
                        binding_item_id=(
                            target.binding_item_id.uuid
                            if target.binding_item_id
                            else None
                        ),
                        catalog_position_id=target.catalog_position_id.uuid,
                        role=target.role.value,
                        content=tuple(
                            PreviewLocalizedContentResponse.from_content(content)
                            for content in target.content
                        ),
                        ready=target.ready,
                        catalog_content=tuple(
                            PreviewLocalizedContentResponse.from_content(content)
                            for content in target.catalog_content
                        ),
                        issues=tuple(
                            PreviewRepresentationIssueResponse.from_issue(issue)
                            for issue in target.issues
                        ),
                    )
                    for target in value.preparation.targets
                ),
            ),
        )
