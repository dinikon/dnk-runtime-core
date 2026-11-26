import { httpClient } from "@/app/providers/http";
import { feedRequest } from "./feed-request";
import {
  type FeedSchema,
  type SavedFeedSchema,
  type SaveFeedSchema,
  type SchemaMetadata,
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
const root = "/console/feed-builder";
export const feedSchemaApi = {
  get(id: string, signal: AbortSignal): Promise<FeedSchema> {
    return feedRequest(async () =>
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
    return feedRequest(async () =>
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
    return feedRequest(async () => {
      const [types, sources, transforms] = await Promise.all([
        httpClient.get<FieldTypesDTO>(`${root}/field-types`, { signal }),
        httpClient.get<SourcePathsDTO>(`${root}/source-paths`, { signal }),
        httpClient.get<TransformsDTO>(`${root}/transforms`, { signal }),
      ]);
      return mapSchemaMetadata(types.data, sources.data, transforms.data);
    });
  },
};
