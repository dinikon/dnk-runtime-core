export type FeedStatus = "DRAFT" | "ACTIVE" | "PAUSED" | "ARCHIVED";
export type ExportFormat = "csv" | "xml";
export type FeedValidationPolicy = "STRICT" | "SKIP_INVALID";
export type FormatSettings =
  | {
      format: "csv";
      delimiter: string;
      encoding: "utf-8";
      includeHeader: boolean;
    }
  | { format: "xml"; rootName: string; itemName: string; encoding: "utf-8" };
export interface ExportSettings {
  formatSettings: FormatSettings;
  productMode: "VARIABLE_TO_SINGLE";
  validationPolicy: FeedValidationPolicy;
}
export type JsonValue =
  null | boolean | number | string | JsonValue[] | { [key: string]: JsonValue };
export interface FeedSettings {
  name: string;
  code: string;
  exportSettings: ExportSettings;
}
export interface Feed extends FeedSettings {
  id: string;
  status: FeedStatus;
  schema: { [key: string]: JsonValue };
  version: number;
  createdAt: string;
  updatedAt: string;
}
export interface FeedListItem {
  id: string;
  name: string;
  code: string;
  status: FeedStatus;
  format: ExportFormat;
  fieldsCount: number;
  version: number;
  createdAt: string;
  updatedAt: string;
}
export interface FeedPage {
  items: FeedListItem[];
  total: number;
  limit: number;
  offset: number;
}
export interface FeedFilters {
  search: string;
  status: FeedStatus | "";
  limit: number;
  offset: number;
}
export interface FeedDraft {
  name: string;
  code: string;
  format: ExportFormat | "";
  delimiter: string;
  includeHeader: boolean;
  rootName: string;
  itemName: string;
  validationPolicy: FeedValidationPolicy;
}
export type FeedFieldErrors = Partial<Record<keyof FeedDraft, string>>;
export interface FeedChanges {
  name?: string;
  code?: string;
  exportSettings?: ExportSettings;
}
export interface UpdateFeed {
  id: string;
  expectedVersion: number;
  changes: FeedChanges;
}
export interface ArchiveFeed {
  id: string;
  expectedVersion: number;
}
export class FeedApiError extends Error {
  constructor(
    public readonly status: number | undefined,
    public readonly fields: FeedFieldErrors = {},
  ) {
    super("Feed request failed");
    this.name = "FeedApiError";
  }
}
