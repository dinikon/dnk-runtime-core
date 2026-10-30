import type {
  ContentFeed,
  FeedPreview,
  FeedImport,
  FeedImportRevisionInput,
  RequestFeedImportInput,
  AttachFeedImportInput,
  ResolveFeedImportInput,
  CreateFeedInput,
  SaveFeedInput,
  FeedRevisionInput,
} from "../model/content-feed.types";
import type {
  ContentFeedDto,
  FeedPreviewDto,
  FeedImportDto,
  FeedImportRevisionDto,
  RequestFeedImportDto,
  AttachFeedImportDto,
  ResolveFeedImportDto,
  CreateContentFeedDto,
  SaveContentFeedDto,
  FeedRevisionDto,
} from "./content-feed.dto";

export function createContentFeedPayload(
  v: CreateFeedInput,
): CreateContentFeedDto {
  return { source_url: v.sourceUrl };
}
export function saveContentFeedPayload(v: SaveFeedInput): SaveContentFeedDto {
  return { source_url: v.sourceUrl, expected_revision: v.expectedRevision };
}
export function contentFeedRevisionPayload(
  v: FeedRevisionInput,
): FeedRevisionDto {
  return { expected_revision: v.expectedRevision };
}

export function mapContentFeed(v: ContentFeedDto): ContentFeed {
  return {
    id: v.id,
    revision: v.revision,
    enabled: v.enabled,
    scopeKey: v.scope_key,
    publicUrl: v.public_url,
    updatedAt: v.updated_at,
  };
}
export function mapFeedPreview(v: FeedPreviewDto): FeedPreview {
  return {
    ready: v.ready,
    statistics: v.statistics
      ? {
          offers: v.statistics.offers,
          changedOffers: v.statistics.changed_offers,
          categories: v.statistics.categories,
        }
      : null,
    issues: v.issues.map((issue) => ({
      code: issue.code,
      publicationId: issue.publication_id,
      field: issue.field,
    })),
  };
}
export function mapFeedImport(v: FeedImportDto): FeedImport {
  return {
    revision: v.revision,
    phase: v.phase,
    operationId: v.operation_id,
    externalId: v.external_import_id,
    submission: v.submission,
    forceUpdate: v.force_update,
    requestedAt: v.requested_at,
    checkedAt: v.last_checked_at,
    finishedAt: v.finished_at,
    errorCode: v.error_code,
    manualResolution: v.manual_resolution,
    report: v.report
      ? {
          status: v.report.status,
          total: v.report.total,
          updated: v.report.updated,
          created: v.report.created,
          imported: v.report.imported,
          notChanged: v.report.not_changed,
          notInFile: v.report.not_in_file,
          withErrors: v.report.with_errors_count,
          issues: v.report.issues.map((i) => ({
            code: i.code,
            stage: i.stage,
          })),
        }
      : null,
    verification: v.verification.map((item) => ({
      publicationId: item.publication_id,
      externalId: item.external_id,
      importKey: item.import_key,
      fields: item.fields.map((f) => ({
        field: f.field,
        locale: f.locale,
        status: f.status,
      })),
      observedGallery: [...item.observed_gallery],
    })),
    recoveryRequired: v.recovery_required,
    canStart: v.can_start,
    canResume: v.can_resume,
    canAttach: v.can_attach,
    canResolve: v.can_resolve,
  };
}
export function feedImportRevision(
  v: FeedImportRevisionInput,
): FeedImportRevisionDto {
  return {
    expected_revision: v.expectedRevision,
    expected_delivery_revision: v.expectedDeliveryRevision,
  };
}
export function requestFeedImportPayload(
  v: RequestFeedImportInput,
): RequestFeedImportDto {
  return {
    ...feedImportRevision(v),
    request_id: v.requestId,
    force_update: v.forceUpdate,
  };
}
export function attachFeedImportPayload(
  v: AttachFeedImportInput,
): AttachFeedImportDto {
  return { ...feedImportRevision(v), external_id: v.externalId };
}
export function resolveFeedImportPayload(
  v: ResolveFeedImportInput,
): ResolveFeedImportDto {
  return {
    ...feedImportRevision(v),
    confirm_not_submitted: v.confirmNotSubmitted,
  };
}
