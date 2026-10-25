export interface ImportMappingDTO {
  target: string;
  source: string | null;
  constant: string | null;
  locale: string | null;
}
export interface ImportConfigurationDTO {
  mappings: ImportMappingDTO[];
  mode: "create" | "update" | "upsert";
  clear_empty: boolean;
  default_locale: string;
  timezone: string;
  encoding: string | null;
  delimiter: string | null;
  record_path: string | null;
}
export interface ImportRunDTO {
  id: string;
  source_name: string;
  status:
    | "preparing"
    | "mapping"
    | "queued"
    | "running"
    | "cancelling"
    | "cancelled"
    | "completed"
    | "completed_with_errors"
    | "failed"
    | "expired";
  version: number;
  total: number;
  processed: number;
  created: number;
  updated: number;
  skipped: number;
  errors: number;
  warnings: number;
  created_at: string;
  finished_at: string | null;
  error: string | null;
}
export interface GetImportResponse {
  run: ImportRunDTO;
  configuration: ImportConfigurationDTO;
  analysis: {
    format: string;
    encoding: string | null;
    delimiter: string | null;
    record_path: string | null;
    candidates: string[];
    fields: { id: string; label: string }[];
    samples: { number: number; values: Record<string, string[]> }[];
    mapped_samples: Record<string, string[]>[];
    warnings: string[];
  };
}
export interface ListImportsResponse {
  items: ImportRunDTO[];
  total: number;
}
export interface ImportRowDTO {
  number: number;
  outcome: string;
  sku: string | null;
  item_id: string | null;
  errors: string[];
  warnings: string[];
}
export interface ListImportRowsResponse {
  items: ImportRowDTO[];
  total: number;
}
export interface CreateImportResponse {
  id: string;
  status: ImportRunDTO["status"];
}
export interface ConfigureImportResponse {
  id: string;
  status: ImportRunDTO["status"];
  version: number;
}
export interface StartImportResponse {
  id: string;
  status: ImportRunDTO["status"];
}
export interface CancelImportResponse {
  id: string;
  status: ImportRunDTO["status"];
}
