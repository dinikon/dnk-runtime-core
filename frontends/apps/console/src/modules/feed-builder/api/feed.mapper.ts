import type {
  Feed,
  FeedListItem,
  FeedSettings,
  ExportSettings,
  UpdateFeed,
} from "../model/feed.types.ts";
import type {
  FeedDTO,
  FeedListItemDTO,
  ExportSettingsDTO,
  CreateFeedDTO,
  PatchFeedDTO,
} from "./feed.dto.ts";
export function exportSettingsPayload(
  value: ExportSettings,
): ExportSettingsDTO {
  const settings = value.formatSettings;
  return {
    format_settings:
      settings.format === "csv"
        ? {
            format: "csv",
            delimiter: settings.delimiter,
            encoding: settings.encoding,
            include_header: settings.includeHeader,
          }
        : {
            format: "xml",
            root_name: settings.rootName,
            item_name: settings.itemName,
            encoding: settings.encoding,
          },
    product_mode: value.productMode,
    validation_policy: value.validationPolicy,
  };
}
export function createFeedPayload(value: FeedSettings): CreateFeedDTO {
  return {
    name: value.name,
    code: value.code,
    export_settings: exportSettingsPayload(value.exportSettings),
  };
}
export function patchFeedPayload(value: UpdateFeed): PatchFeedDTO {
  return {
    expected_version: value.expectedVersion,
    ...(value.changes.name !== undefined ? { name: value.changes.name } : {}),
    ...(value.changes.code !== undefined ? { code: value.changes.code } : {}),
    ...(value.changes.exportSettings
      ? { export_settings: exportSettingsPayload(value.changes.exportSettings) }
      : {}),
  };
}
export function mapFeed(value: FeedDTO): Feed {
  const settings = value.export_settings.format_settings;
  return {
    id: value.id,
    name: value.name,
    code: value.code,
    status: value.status,
    version: value.version,
    schema: structuredClone(value.schema),
    createdAt: value.created_at,
    updatedAt: value.updated_at,
    exportSettings: {
      formatSettings:
        settings.format === "csv"
          ? {
              format: "csv",
              delimiter: settings.delimiter,
              encoding: settings.encoding,
              includeHeader: settings.include_header,
            }
          : {
              format: "xml",
              rootName: settings.root_name,
              itemName: settings.item_name,
              encoding: settings.encoding,
            },
      productMode: value.export_settings.product_mode,
      validationPolicy: value.export_settings.validation_policy,
    },
  };
}
export function mapFeedListItem(value: FeedListItemDTO): FeedListItem {
  return {
    id: value.id,
    name: value.name,
    code: value.code,
    status: value.status,
    format: value.format,
    fieldsCount: value.fields_count,
    version: value.version,
    createdAt: value.created_at,
    updatedAt: value.updated_at,
  };
}
