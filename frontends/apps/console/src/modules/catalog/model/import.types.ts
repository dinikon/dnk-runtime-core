export type ImportStatus =
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
export interface ImportMapping {
  target: string;
  source: string | null;
  constant: string | null;
  locale: string | null;
}
export interface ImportConfiguration {
  mappings: ImportMapping[];
  mode: "create" | "update" | "upsert";
  clearEmpty: boolean;
  defaultLocale: string;
  timezone: string;
  encoding: string | null;
  delimiter: string | null;
  recordPath: string | null;
}
export interface CatalogImportRun {
  id: string;
  name: string;
  status: ImportStatus;
  version: number;
  generation: number;
  canResume: boolean;
  total: number;
  processed: number;
  created: number;
  updated: number;
  skipped: number;
  errors: number;
  warnings: number;
  createdAt: Date;
  finishedAt: Date | null;
  error: string | null;
}
export interface ImportField {
  id: string;
  label: string;
}
export interface ImportSample {
  number: number;
  values: Record<string, string[]>;
}
export interface CatalogImportDetails {
  run: CatalogImportRun;
  configuration: ImportConfiguration;
  analysis: {
    format: string;
    encoding: string | null;
    delimiter: string | null;
    recordPath: string | null;
    candidates: string[];
    fields: ImportField[];
    samples: ImportSample[];
    mappedSamples: Record<string, string[]>[];
    warnings: string[];
  };
}
export interface CatalogImportRow {
  number: number;
  outcome: string;
  sku: string | null;
  itemId: string | null;
  errors: string[];
  warnings: string[];
}
export interface ImportSourceValues {
  file: File | null;
  url: string;
  defaultLocale: string;
  timezone: string;
  key: string;
}
export interface ImportPage {
  items: CatalogImportRun[];
  total: number;
}
export interface ImportRowsPage {
  items: CatalogImportRow[];
  total: number;
}
export interface ImportActionResult {
  id: string;
  status: ImportStatus;
  version?: number;
  generation?: number;
}
