import type {
  ExportIssueSeverity,
  FeedExportOutcome,
  FeedRefreshStatus,
} from "../model/feed-export.types";
import type { ExportFormat, FeedValidationPolicy } from "../model/feed.types";
import type { FeedAccessMode } from "../model/feed-access.types";

export interface ExportTaskDTO {
  status: FeedRefreshStatus;
  requested_at: string;
  started_at: string | null;
}
export interface ExportReportDTO {
  completed_at: string;
  as_of: string | null;
  validation_policy: FeedValidationPolicy;
  outcome: FeedExportOutcome;
  reason_code: string | null;
  is_complete: boolean;
  total_items: number;
  valid_items: number;
  warning_items: number;
  rejected_items: number;
}
export interface ActiveFeedFileDTO {
  url: string;
  format: ExportFormat;
  as_of: string;
  published_at: string;
}
export interface FeedExportStateDTO {
  feed_version: number;
  can_refresh: boolean;
  can_rotate: boolean;
  can_manage_access: boolean;
  access_mode: FeedAccessMode;
  task: ExportTaskDTO | null;
  report: ExportReportDTO | null;
  active: ActiveFeedFileDTO | null;
}
export interface FeedExportIssueDTO {
  publication_id: string;
  severity: ExportIssueSeverity;
  code: string;
  message: string;
  sku: string | null;
  field_id: string | null;
  rule_id: string | null;
  path: (string | number)[];
}
export interface FeedExportIssuesDTO {
  items: FeedExportIssueDTO[];
  total: number;
}
export interface RequestFeedRefreshDTO {
  status: FeedRefreshStatus;
  requested_at: string;
}
export interface RotatedFeedLinkDTO {
  url: string;
  feed_version: number;
}
