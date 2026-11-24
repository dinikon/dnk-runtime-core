import type {
  FeedExportIssuesDTO,
  FeedExportStateDTO,
} from "./feed-export.dto";
import type {
  FeedExportIssues,
  FeedExportState,
} from "../model/feed-export.types";

export function mapFeedExport(dto: FeedExportStateDTO): FeedExportState {
  const { task, report, active } = dto;
  return {
    feedVersion: dto.feed_version,
    canRefresh: dto.can_refresh,
    canRotate: dto.can_rotate,
    task: task && {
      status: task.status,
      requestedAt: task.requested_at,
      startedAt: task.started_at,
    },
    report: report && {
      completedAt: report.completed_at,
      asOf: report.as_of,
      validationPolicy: report.validation_policy,
      outcome: report.outcome,
      reasonCode: report.reason_code,
      isComplete: report.is_complete,
      totalItems: report.total_items,
      validItems: report.valid_items,
      warningItems: report.warning_items,
      rejectedItems: report.rejected_items,
    },
    active: active && {
      url: active.url,
      format: active.format,
      asOf: active.as_of,
      publishedAt: active.published_at,
    },
  };
}
export function mapFeedExportIssues(
  dto: FeedExportIssuesDTO,
): FeedExportIssues {
  return {
    total: dto.total,
    items: dto.items.map((issue) => ({
      publicationId: issue.publication_id,
      severity: issue.severity,
      code: issue.code,
      message: issue.message,
      sku: issue.sku,
      fieldId: issue.field_id,
      ruleId: issue.rule_id,
      path: issue.path,
    })),
  };
}
