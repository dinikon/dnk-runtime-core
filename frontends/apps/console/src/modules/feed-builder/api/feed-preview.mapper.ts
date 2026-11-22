import type {
  FeedPreview,
  FeedPreviewIssue,
  TestCsvIssue,
} from "../model/feed-preview.types";
import type {
  FeedPreviewDTO,
  FeedPreviewIssueDTO,
  TestCsvIssueDTO,
} from "./feed-preview.dto";

function mapIssue(issue: FeedPreviewIssueDTO): FeedPreviewIssue {
  return {
    fieldId: issue.field_id,
    code: issue.code,
    message: issue.message,
    path: issue.path,
    ruleId: issue.rule_id,
  };
}

export function mapFeedPreview(dto: FeedPreviewDTO): FeedPreview {
  return {
    feedId: dto.feed_id,
    version: dto.version,
    asOf: dto.as_of,
    totalEnabled: dto.total_enabled,
    columns: dto.columns.map((column) => ({
      fieldId: column.field_id,
      name: column.name,
    })),
    rows: dto.rows.map((row) => ({
      publicationId: row.publication_id,
      itemId: row.catalog_item_id,
      variantId: row.catalog_variant_id,
      sku: row.sku,
      values: row.values,
      issues: row.issues.map(mapIssue),
      readiness: row.readiness,
    })),
  };
}

export function mapTestCsvIssue(issue: TestCsvIssueDTO): TestCsvIssue {
  return {
    ...mapIssue(issue),
    publicationId: issue.publication_id,
    itemId: issue.catalog_item_id,
    variantId: issue.catalog_variant_id,
    sku: issue.sku,
    fieldName: issue.field_name,
  };
}
