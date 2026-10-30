import type {
  PreviewRepresentationResponseDto,
  RepresentationFieldOriginDto,
  RepresentationIssueDto,
  RepresentationContentDto,
  RepresentationDetailsFieldsDto,
  RepresentationOverridesDto,
  LocalizedOverridesDto,
  SaveRepresentationRequestDto,
  RepresentationVersionDto,
} from "./representation.dto";
import type {
  RepresentationPreview,
  RepresentationFieldOrigin,
  RepresentationIssue,
  RepresentationContent,
  RepresentationDetails,
  RepresentationOverrides,
  LocalizedOverrides,
  RepresentationDraftInput,
  RepresentationVersion,
} from "../model/representation.types";

function origin(
  value: RepresentationFieldOriginDto,
): RepresentationFieldOrigin {
  return { kind: value.kind, catalogPositionId: value.catalog_position_id };
}
function issue(value: RepresentationIssueDto): RepresentationIssue {
  return {
    code: value.code,
    publicationId: value.publication_id,
    field: value.field,
    locale: value.locale,
  };
}
function content(value: RepresentationContentDto): RepresentationContent {
  return {
    locale: value.locale,
    title: value.title,
    body: value.body,
    gallery:
      value.gallery?.map((image) => ({
        fileId: image.file_id,
        alt: image.alt,
        caption: image.caption,
      })) ?? null,
    origins: {
      title: origin(value.origins.title),
      body: origin(value.origins.body),
      gallery: origin(value.origins.gallery),
    },
  };
}
export function representationPreview(
  dto: PreviewRepresentationResponseDto,
): RepresentationPreview {
  const value = dto.representation;
  return {
    channelId: value.channel_id,
    connectionId: value.connection_id,
    bindingGroupId: value.binding_group_id,
    bindingRevision: value.binding_revision,
    configRevision: value.config_revision,
    platform: value.platform,
    mode: value.mode,
    locales: [...value.locales],
    asOf: value.as_of,
    bindingState: value.binding_state,
    issues: value.issues.map(issue),
    exportBlockers: [...dto.export_blockers],
    draft: dto.draft,
    targets: value.targets.map((target) => ({
      publicationId: target.publication_id,
      externalId: target.external_id,
      parentPublicationId: target.parent_publication_id,
      publicationKind: target.publication_kind,
      bindingItemId: target.binding_item_id,
      catalogPositionId: target.catalog_position_id,
      role: target.role,
      ready: target.ready,
      issues: target.issues.map(issue),
      content: target.content.map(content),
      catalogContent: target.catalog_content.map(content),
    })),
  };
}
function localizedOverrides(value: LocalizedOverridesDto): LocalizedOverrides {
  return {
    title: value.title,
    body: value.body,
    gallery:
      value.gallery == null
        ? value.gallery
        : value.gallery.map((image) => ({
            fileId: image.file_id,
            alt: image.alt,
            caption: image.caption,
          })),
  };
}
export function representationOverrides(
  value: RepresentationOverridesDto,
): RepresentationOverrides {
  return {
    common: Object.fromEntries(
      Object.entries(value.common).map(([locale, fields]) => [
        locale,
        localizedOverrides(fields),
      ]),
    ),
    items: Object.fromEntries(
      Object.entries(value.items).map(([id, locales]) => [
        id,
        Object.fromEntries(
          Object.entries(locales).map(([locale, fields]) => [
            locale,
            localizedOverrides(fields),
          ]),
        ),
      ]),
    ),
  };
}
export function representationDetails(
  value: RepresentationDetailsFieldsDto,
): RepresentationDetails {
  return {
    state: {
      id: value.state.id,
      revision: value.state.revision,
      exportEnabled: value.state.export_enabled,
      overrides: representationOverrides(value.state.overrides),
      createdAt: value.state.created_at,
      updatedAt: value.state.updated_at,
      createdBy: value.state.created_by,
      updatedBy: value.state.updated_by,
    },
    bindingRevision: value.binding_revision,
    configRevision: value.config_revision,
    locales: [...value.locales],
    items: value.items.map((item) => ({
      id: item.id,
      catalogPositionId: item.catalog_position_id,
      publicationId: item.publication_id,
    })),
  };
}
function localizedPayload(value: LocalizedOverrides): LocalizedOverridesDto {
  return {
    ...(value.title != null ? { title: value.title } : {}),
    ...(value.body != null ? { body: value.body } : {}),
    ...(value.gallery != null
      ? {
          gallery: value.gallery.map((image) => ({
            file_id: image.fileId,
            alt: image.alt,
            caption: image.caption,
          })),
        }
      : {}),
  };
}
export function representationVersionPayload(
  value: RepresentationVersion,
): RepresentationVersionDto {
  return {
    expected_revision: value.expectedRevision,
    expected_binding_revision: value.expectedBindingRevision,
    expected_config_revision: value.expectedConfigRevision,
  };
}
export function representationDraftPayload(
  value: RepresentationDraftInput,
): SaveRepresentationRequestDto {
  return {
    ...representationVersionPayload(value),
    overrides: {
      common: Object.fromEntries(
        Object.entries(value.overrides.common).map(([locale, fields]) => [
          locale,
          localizedPayload(fields),
        ]),
      ),
      items: Object.fromEntries(
        Object.entries(value.overrides.items).map(([id, locales]) => [
          id,
          Object.fromEntries(
            Object.entries(locales).map(([locale, fields]) => [
              locale,
              localizedPayload(fields),
            ]),
          ),
        ]),
      ),
    },
  };
}
