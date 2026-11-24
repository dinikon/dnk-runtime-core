import type {
  FeedStatus,
  ExportFormat,
  FeedValidationPolicy,
  JsonValue,
} from "../model/feed.types";
export type FormatSettingsDTO =
  | {
      format: "csv";
      delimiter: string;
      encoding: "utf-8";
      include_header: boolean;
    }
  | { format: "xml"; root_name: string; item_name: string; encoding: "utf-8" };
export interface ExportSettingsDTO {
  format_settings: FormatSettingsDTO;
  product_mode: "VARIABLE_TO_SINGLE";
  validation_policy: FeedValidationPolicy;
}
export interface CreateFeedDTO {
  name: string;
  code: string;
  export_settings: ExportSettingsDTO;
}
export interface PatchFeedDTO {
  expected_version: number;
  name?: string;
  code?: string;
  export_settings?: ExportSettingsDTO;
}
export interface FeedDTO extends CreateFeedDTO {
  id: string;
  status: FeedStatus;
  schema: { [key: string]: JsonValue };
  version: number;
  created_at: string;
  updated_at: string;
}
export interface FeedListItemDTO {
  id: string;
  name: string;
  code: string;
  status: FeedStatus;
  format: ExportFormat;
  fields_count: number;
  version: number;
  created_at: string;
  updated_at: string;
}
export interface FeedPageDTO {
  items: FeedListItemDTO[];
  total: number;
  limit: number;
  offset: number;
}
