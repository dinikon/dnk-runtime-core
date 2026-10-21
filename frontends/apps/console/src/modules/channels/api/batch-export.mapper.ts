import type * as DTO from "./batch-export.dto";
import type * as Model from "../model/batch-export.types";
export function mapBatchStatus(status: string): Model.BatchExportStatus {
  const known: Model.BatchExportStatus[] = [
    "preparing",
    "checking",
    "building",
    "ready",
    "submitting",
    "processing",
    "verifying",
    "unknown",
    "succeeded",
    "partial",
    "failed",
    "empty",
    "prepared",
  ];
  return known.find((value) => value === status) ?? "unknown";
}
export function mapBatchSummary(
  dto: DTO.BatchExportSummaryDto,
): Model.BatchExportSummary {
  return {
    id: dto.id,
    channelId: dto.channel_id,
    trigger: dto.trigger,
    status: mapBatchStatus(dto.status),
    createdAt: dto.created_at,
    updatedAt: dto.updated_at,
    errorCode: dto.error_code,
    counts: dto.counts,
    interrupted: dto.interrupted,
    deliveryMode: dto.delivery_mode,
  };
}
export function mapBatchOverview(
  dto: DTO.BatchExportOverviewDto,
): Model.BatchExportOverview {
  return {
    outboundEnabled: dto.outbound_enabled,
    deliveryConfigured: dto.delivery_configured,
    feedAvailable: dto.feed_available,
    boundCount: dto.bound_count,
    enabledCount: dto.enabled_count,
    schedule: {
      enabled: dto.schedule.enabled,
      hour: dto.schedule.hour,
      minute: dto.schedule.minute,
      timezone: dto.schedule.timezone,
      revision: dto.schedule.revision,
      nextAt: dto.schedule.next_at,
    },
    recent: dto.recent.map(mapBatchSummary),
  };
}
export function mapBatchDetail(
  dto: DTO.BatchExportDetailDto,
): Model.BatchExportDetail {
  return {
    run: mapBatchSummary(dto.run),
    feedUrl: dto.feed_url,
    feedExpiresAt: dto.feed_expires_at,
    total: dto.total,
    items: dto.items.map((item) => ({
      publicationId: item.publication_id,
      catalogItemId: item.catalog_item_id,
      externalId: item.external_id,
      status: item.status,
      issues: item.issues,
      titles: item.titles,
    })),
  };
}
export function schedulePayload(
  input: Model.ExportScheduleInput,
): DTO.ExportScheduleRequestDto {
  return {
    enabled: input.enabled,
    hour: input.hour,
    minute: input.minute,
    timezone: input.timezone,
    expected_revision: input.expectedRevision,
  };
}
export function publicationExportPayload(
  input: Model.SetPublicationExportInput,
): DTO.SetPublicationExportRequestDto {
  return {
    enabled: input.enabled,
    items: input.items.map((item) => ({
      representation_id: item.representationId,
      expected_revision: item.expectedRevision,
    })),
  };
}
