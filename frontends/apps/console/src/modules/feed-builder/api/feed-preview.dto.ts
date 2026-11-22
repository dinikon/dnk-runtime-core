export interface FeedPreviewIssueDTO {
  field_id: string | null;
  code: string;
  message: string;
  path: (string | number)[];
  rule_id: string | null;
}

export interface FeedPreviewDTO {
  feed_id: string;
  version: number;
  as_of: string;
  total_enabled: number;
  columns: { field_id: string; name: string }[];
  rows: {
    publication_id: string;
    catalog_item_id: string;
    catalog_variant_id: string | null;
    sku: string | null;
    values: (string | null)[];
    issues: FeedPreviewIssueDTO[];
    readiness: "READY" | "NEEDS_INPUT" | "INVALID";
  }[];
}

export interface TestCsvIssueDTO extends FeedPreviewIssueDTO {
  publication_id: string;
  catalog_item_id: string;
  catalog_variant_id: string | null;
  sku: string | null;
  field_name: string | null;
}

export interface FeedPreviewErrorDTO {
  detail?: string | { message?: string; issues?: TestCsvIssueDTO[] };
}
