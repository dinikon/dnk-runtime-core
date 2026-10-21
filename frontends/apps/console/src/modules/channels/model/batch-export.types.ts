export type BatchExportStatus =
  | "preparing"
  | "checking"
  | "building"
  | "ready"
  | "submitting"
  | "processing"
  | "verifying"
  | "unknown"
  | "succeeded"
  | "partial"
  | "failed"
  | "empty"
  | "prepared";
export interface BatchExportSummary {
  id: string;
  channelId: string;
  trigger: string;
  status: BatchExportStatus;
  createdAt: string;
  updatedAt: string;
  errorCode: string | null;
  counts: Record<string, number>;
  interrupted: boolean;
  deliveryMode: "provider" | "file";
}
export interface ExportSchedule {
  enabled: boolean;
  hour: number;
  minute: number;
  timezone: string;
  revision: number;
  nextAt: string | null;
}
export interface BatchExportOverview {
  outboundEnabled: boolean;
  deliveryConfigured: boolean;
  feedAvailable: boolean;
  boundCount: number;
  enabledCount: number;
  schedule: ExportSchedule;
  recent: BatchExportSummary[];
}
export interface BatchExportItem {
  publicationId: string;
  catalogItemId: string;
  externalId: string;
  status: string;
  issues: string[];
  titles: Record<string, string>;
}
export interface BatchExportDetail {
  feedUrl: string | null;
  feedExpiresAt: string | null;
  run: BatchExportSummary;
  items: BatchExportItem[];
  total: number;
}
export interface ExportScheduleInput {
  channelId: string;
  enabled: boolean;
  hour: number;
  minute: number;
  timezone: string;
  expectedRevision: number;
}
export interface StartBatchExportInput {
  channelId: string;
  runId: string;
  deliveryMode: "provider" | "file";
}
export interface SetPublicationExportInput {
  channelId: string;
  enabled: boolean;
  items: { representationId: string; expectedRevision: number }[];
}
export interface BatchExportPageInput {
  runId: string;
  offset: number;
  limit: number;
}
