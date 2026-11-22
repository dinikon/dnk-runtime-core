import { isAxiosError } from "axios";
import { httpClient } from "@/app/providers/http";
import {
  SchemaApiError,
  type FeedSchema,
  type SavedFeedSchema,
  type SaveFeedSchema,
  type SchemaMetadata,
  type SchemaIssue,
} from "../model/feed-schema.types";
import type {
  FeedSchemaDTO,
  SavedFeedSchemaDTO,
  FieldTypesDTO,
  SourcePathsDTO,
  TransformsDTO,
} from "./feed-schema.dto";
import {
  mapFeedSchema,
  mapSavedSchema,
  saveSchemaPayload,
  mapSchemaMetadata,
} from "./feed-schema.mapper";
export async function schemaRequest<T>(run: () => Promise<T>): Promise<T> {
  try {
    return await run();
  } catch (error: unknown) {
    if (!isAxiosError(error)) throw error;
    const detail: unknown = error.response?.data?.detail;
    const issues: SchemaIssue[] = [];
    if (Array.isArray(detail))
      for (const issue of detail) {
        if (typeof issue !== "object" || !issue || !Array.isArray(issue.loc))
          continue;
        issues.push({
          code: "SCHEMA_INVALID",
          message: "Проверьте значение и тип настройки.",
          path: issue.loc
            .filter(
              (p: unknown) => typeof p === "string" || typeof p === "number",
            )
            .filter((p: string | number) => p !== "body"),
        });
      }
    else if (
      detail &&
      typeof detail === "object" &&
      "message" in detail &&
      typeof detail.message === "string"
    ) {
      const d = detail as Record<string, unknown>;
      issues.push({
        code: typeof d.code === "string" ? d.code : "SCHEMA_INVALID",
        message: detail.message,
        fieldId: typeof d.field_id === "string" ? d.field_id : undefined,
        path: Array.isArray(d.path)
          ? d.path.filter(
              (p: unknown) => typeof p === "string" || typeof p === "number",
            )
          : [],
      });
    }
    throw new SchemaApiError(error.response?.status, issues);
  }
}
const root = "/console/feed-builder";
export const feedSchemaApi = {
  get(id: string, signal: AbortSignal): Promise<FeedSchema> {
    return schemaRequest(async () =>
      mapFeedSchema(
        (
          await httpClient.get<FeedSchemaDTO>(
            `${root}/feeds/${encodeURIComponent(id)}/schema`,
            { signal },
          )
        ).data,
      ),
    );
  },
  save(value: SaveFeedSchema, signal: AbortSignal): Promise<SavedFeedSchema> {
    return schemaRequest(async () =>
      mapSavedSchema(
        (
          await httpClient.put<SavedFeedSchemaDTO>(
            `${root}/feeds/${encodeURIComponent(value.id)}/schema/draft`,
            saveSchemaPayload(value),
            { signal },
          )
        ).data,
      ),
    );
  },
  metadata(signal: AbortSignal): Promise<SchemaMetadata> {
    return schemaRequest(async () => {
      const [types, sources, transforms] = await Promise.all([
        httpClient.get<FieldTypesDTO>(`${root}/field-types`, { signal }),
        httpClient.get<SourcePathsDTO>(`${root}/source-paths`, { signal }),
        httpClient.get<TransformsDTO>(`${root}/transforms`, { signal }),
      ]);
      return mapSchemaMetadata(types.data, sources.data, transforms.data);
    });
  },
};
