import type { PreviewCategory } from "./feed-categories.types";
export interface FeedPreviewRequest {
  feedId: string;
  expectedVersion: number;
}

export interface FeedPreviewIssue {
  fieldId: string | null;
  code: string;
  message: string;
  path: (string | number)[];
  ruleId: string | null;
}

export interface FeedPreviewRow {
  publicationId: string;
  itemId: string;
  variantId: string | null;
  sku: string | null;
  values: (string | null)[];
  issues: FeedPreviewIssue[];
  categories?: PreviewCategory[];
  readiness: "READY" | "NEEDS_INPUT" | "INVALID";
}

export interface FeedPreview {
  feedId: string;
  version: number;
  asOf: string;
  totalEnabled: number;
  columns: { fieldId: string; name: string; xmlAttribute: boolean }[];
  rows: FeedPreviewRow[];
}

export interface TestCsvIssue extends FeedPreviewIssue {
  publicationId: string;
  itemId: string;
  variantId: string | null;
  sku: string | null;
  fieldName: string | null;
}

export class FeedPreviewError extends Error {
  constructor(
    message: string,
    public readonly status?: number,
    public readonly issues: TestCsvIssue[] = [],
  ) {
    super(message);
    this.name = "FeedPreviewError";
  }
}
