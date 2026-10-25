import type {
  CatalogImportDetails,
  CatalogImportRun,
  ImportConfiguration,
  CatalogImportRow,
} from "../model/import.types";
import type {
  ImportRunDTO,
  ImportConfigurationDTO,
  GetImportResponse,
  ImportRowDTO,
} from "./import.dto";
export function importRunFromDto(dto: ImportRunDTO): CatalogImportRun {
  return {
    id: dto.id,
    name: dto.source_name,
    status: dto.status,
    version: dto.version,
    generation: dto.generation,
    canResume: dto.can_resume,
    total: dto.total,
    processed: dto.processed,
    created: dto.created,
    updated: dto.updated,
    skipped: dto.skipped,
    errors: dto.errors,
    warnings: dto.warnings,
    createdAt: new Date(dto.created_at),
    finishedAt: dto.finished_at ? new Date(dto.finished_at) : null,
    error: dto.error,
  };
}
export function importConfigurationToDto(
  value: ImportConfiguration,
): ImportConfigurationDTO {
  return {
    mappings: value.mappings.map((m) => ({ ...m })),
    mode: value.mode,
    clear_empty: value.clearEmpty,
    default_locale: value.defaultLocale,
    timezone: value.timezone,
    encoding: value.encoding,
    delimiter: value.delimiter,
    record_path: value.recordPath,
  };
}
export function importDetailsFromDto(
  dto: GetImportResponse,
): CatalogImportDetails {
  const c = dto.configuration,
    a = dto.analysis;
  return {
    run: importRunFromDto(dto.run),
    configuration: {
      mappings: c.mappings.map((m) => ({ ...m })),
      mode: c.mode,
      clearEmpty: c.clear_empty,
      defaultLocale: c.default_locale,
      timezone: c.timezone,
      encoding: c.encoding,
      delimiter: c.delimiter,
      recordPath: c.record_path,
    },
    analysis: {
      format: a.format,
      encoding: a.encoding,
      delimiter: a.delimiter,
      recordPath: a.record_path,
      candidates: [...a.candidates],
      fields: a.fields.map((f) => ({ ...f })),
      samples: a.samples.map((s) => ({
        number: s.number,
        values: Object.fromEntries(
          Object.entries(s.values).map(([k, v]) => [k, [...v]]),
        ),
      })),
      mappedSamples: a.mapped_samples.map((v) => ({ ...v })),
      warnings: [...a.warnings],
    },
  };
}
export function importRowFromDto(dto: ImportRowDTO): CatalogImportRow {
  return {
    number: dto.number,
    outcome: dto.outcome,
    sku: dto.sku,
    itemId: dto.item_id,
    errors: [...dto.errors],
    warnings: [...dto.warnings],
  };
}
