import type { ExportFormat, FeedValidationPolicy } from "./feed.types";
import type { FeedAccessMode } from "./feed-access.types";

export type ExportIssueSeverity = "ERROR" | "WARNING";
export type FeedRefreshStatus = "PENDING" | "RUNNING";
export type FeedExportOutcome = "PUBLISHED" | "REJECTED" | "FAILED";

export interface FeedExportTask {
  status: FeedRefreshStatus;
  requestedAt: string;
  startedAt: string | null;
}
export interface FeedExportReport {
  completedAt: string;
  asOf: string | null;
  validationPolicy: FeedValidationPolicy;
  outcome: FeedExportOutcome;
  reasonCode: string | null;
  isComplete: boolean;
  totalItems: number;
  validItems: number;
  warningItems: number;
  rejectedItems: number;
}
export interface ActiveFeedFile {
  url: string;
  format: ExportFormat;
  asOf: string;
  publishedAt: string;
}
export interface FeedExportState {
  feedVersion: number;
  canRefresh: boolean;
  canRotate: boolean;
  canManageAccess: boolean;
  accessMode: FeedAccessMode;
  task: FeedExportTask | null;
  report: FeedExportReport | null;
  active: ActiveFeedFile | null;
}
export interface FeedExportIssue {
  publicationId: string;
  severity: ExportIssueSeverity;
  code: string;
  message: string;
  sku: string | null;
  fieldId: string | null;
  ruleId: string | null;
  path: (string | number)[];
}
export interface FeedExportIssues {
  items: FeedExportIssue[];
  total: number;
}
export interface FeedExportAction {
  feedId: string;
  version: number;
}
export interface RotatedFeedLink {
  url: string;
  feedVersion: number;
}
