export interface BatchExportSummaryDto {
  id: string;
  channel_id: string;
  trigger: string;
  status: string;
  created_at: string;
  updated_at: string;
  error_code: string | null;
  counts: Record<string, number>;
  interrupted: boolean;
  delivery_mode: "provider" | "file";
}
export interface ExportScheduleDto {
  enabled: boolean;
  hour: number;
  minute: number;
  timezone: string;
  revision: number;
  next_at: string | null;
}
export interface BatchExportOverviewDto {
  outbound_enabled: boolean;
  delivery_configured: boolean;
  feed_available: boolean;
  bound_count: number;
  enabled_count: number;
  schedule: ExportScheduleDto;
  recent: BatchExportSummaryDto[];
}
export interface BatchExportDetailDto {
  feed_url: string | null;
  feed_expires_at: string | null;
  run: BatchExportSummaryDto;
  items: {
    publication_id: string;
    catalog_item_id: string;
    external_id: string;
    status: string;
    issues: string[];
    titles: Record<string, string>;
  }[];
  total: number;
}
export interface StartBatchExportRequestDto {
  run_id: string;
  delivery_mode: "provider" | "file";
}
export interface StartBatchExportResponseDto {
  run_id: string;
}
export interface ExportScheduleRequestDto {
  enabled: boolean;
  hour: number;
  minute: number;
  timezone: string;
  expected_revision: number;
}
export interface UpdateExportScheduleResponseDto {
  revision: number;
  next_at: string | null;
}
export interface SetPublicationExportRequestDto {
  enabled: boolean;
  items: { representation_id: string; expected_revision: number }[];
}
export interface SetPublicationExportResponseDto {
  revisions: Record<string, number>;
}
