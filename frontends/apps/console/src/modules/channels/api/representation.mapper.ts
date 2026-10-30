import type {
  PreviewRepresentationResponseDto,
  RepresentationFieldOriginDto,
  RepresentationIssueDto,
} from "./representation.dto";
import type {
  RepresentationPreview,
  RepresentationFieldOrigin,
  RepresentationIssue,
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
      content: target.content.map((content) => ({
        locale: content.locale,
        title: content.title,
        body: content.body,
        gallery:
          content.gallery?.map((image) => ({
            fileId: image.file_id,
            alt: image.alt,
            caption: image.caption,
          })) ?? null,
        origins: {
          title: origin(content.origins.title),
          body: origin(content.origins.body),
          gallery: origin(content.origins.gallery),
        },
      })),
    })),
  };
}
