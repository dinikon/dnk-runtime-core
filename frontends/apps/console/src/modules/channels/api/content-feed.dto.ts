export interface ContentFeedDto {
  id: string;
  revision: number;
  enabled: boolean;
  scope_key: string;
  source_schema: string;
  source_settings: { base_locale: string };
  public_url: string | null;
  created_at: string;
  updated_at: string;
}
export interface FeedPreviewDto {
  ready: boolean;
  statistics: {
    offers: number;
    changed_offers: number;
    categories: number;
  } | null;
  issues: {
    code: string;
    publication_id: string | null;
    field: string | null;
  }[];
}
export interface FeedImportDto {
  revision: number;
  phase:
    | "idle"
    | "queued"
    | "submitting"
    | "processing"
    | "verifying"
    | "completed"
    | "failed"
    | "unknown"
    | "needs_attention"
    | "resolved";
  operation_id: string | null;
  external_import_id: string | null;
  submission:
    "not_sent" | "queued" | "submitting" | "accepted" | "rejected" | "unknown";
  force_update: boolean;
  requested_at: string | null;
  submission_started_at: string | null;
  last_checked_at: string | null;
  finished_at: string | null;
  error_code: string | null;
  manual_resolution: string | null;
  report: {
    status: "SUCCESS" | "PARTIAL" | "FATAL";
    total: number | null;
    updated: number | null;
    created: number | null;
    imported: number | null;
    not_changed: number | null;
    not_in_file: number | null;
    with_errors_count: number | null;
    issues: { code: string; stage: string }[];
  } | null;
  verification: {
    publication_id: string;
    external_id: string;
    import_key: string;
    fields: {
      field: "title" | "body" | "gallery";
      locale: string | null;
      status: "confirmed" | "mismatch" | "unconfirmed" | "obsolete";
    }[];
    observed_gallery: string[];
  }[];
  recovery_required: boolean;
  can_start: boolean;
  can_resume: boolean;
  can_attach: boolean;
  can_resolve: boolean;
}
export interface FeedImportRevisionDto {
  expected_revision: number;
  expected_delivery_revision: number;
}
export interface CreateContentFeedDto {
  source_url: string;
}
export interface SaveContentFeedDto extends CreateContentFeedDto {
  expected_revision: number;
}
export interface FeedRevisionDto {
  expected_revision: number;
}
export interface RequestFeedImportDto extends FeedImportRevisionDto {
  request_id: string;
  force_update: boolean;
}
export interface AttachFeedImportDto extends FeedImportRevisionDto {
  external_id: string;
}
export interface ResolveFeedImportDto extends FeedImportRevisionDto {
  confirm_not_submitted: true;
}
