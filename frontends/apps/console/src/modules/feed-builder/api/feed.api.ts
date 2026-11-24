import { isAxiosError } from "axios";
import { httpClient } from "@/app/providers/http";
import {
  FeedApiError,
  type Feed,
  type FeedPage,
  type FeedFilters,
  type FeedSettings,
  type UpdateFeed,
  type ArchiveFeed,
  type FeedFieldErrors,
} from "../model/feed.types";
import type { FeedDTO, FeedPageDTO } from "./feed.dto";
import {
  createFeedPayload,
  patchFeedPayload,
  mapFeed,
  mapFeedListItem,
} from "./feed.mapper";
const root = "/console/feed-builder/feeds";
const fieldNames: Record<string, keyof FeedFieldErrors> = {
  name: "name",
  code: "code",
  format: "format",
  delimiter: "delimiter",
  include_header: "includeHeader",
  root_name: "rootName",
  item_name: "itemName",
  validation_policy: "validationPolicy",
};
async function request<T>(run: () => Promise<T>): Promise<T> {
  try {
    return await run();
  } catch (error: unknown) {
    if (!isAxiosError(error)) throw error;
    const fields: FeedFieldErrors = {};
    const detail: unknown = error.response?.data?.detail;
    if (Array.isArray(detail))
      for (const issue of detail) {
        if (
          typeof issue !== "object" ||
          issue === null ||
          !Array.isArray(issue.loc)
        )
          continue;
        const key = fieldNames[String(issue.loc.at(-1))];
        if (key) fields[key] = "Проверьте значение поля.";
      }
    throw new FeedApiError(error.response?.status, fields);
  }
}
export const feedApi = {
  list(filters: FeedFilters, signal: AbortSignal): Promise<FeedPage> {
    return request(async () => {
      const { data } = await httpClient.get<FeedPageDTO>(root, {
        signal,
        params: {
          search: filters.search || undefined,
          status: filters.status || undefined,
          limit: filters.limit,
          offset: filters.offset,
        },
      });
      return { ...data, items: data.items.map(mapFeedListItem) };
    });
  },
  get(id: string, signal: AbortSignal): Promise<Feed> {
    return request(async () =>
      mapFeed(
        (
          await httpClient.get<FeedDTO>(`${root}/${encodeURIComponent(id)}`, {
            signal,
          })
        ).data,
      ),
    );
  },
  create(value: FeedSettings, signal: AbortSignal): Promise<Feed> {
    return request(async () =>
      mapFeed(
        (
          await httpClient.post<FeedDTO>(root, createFeedPayload(value), {
            signal,
          })
        ).data,
      ),
    );
  },
  update(value: UpdateFeed, signal: AbortSignal): Promise<Feed> {
    return request(async () =>
      mapFeed(
        (
          await httpClient.patch<FeedDTO>(
            `${root}/${encodeURIComponent(value.id)}`,
            patchFeedPayload(value),
            { signal },
          )
        ).data,
      ),
    );
  },
  archive(value: ArchiveFeed, signal: AbortSignal): Promise<void> {
    return request(async () => {
      await httpClient.delete(`${root}/${encodeURIComponent(value.id)}`, {
        signal,
        params: { expected_version: value.expectedVersion },
      });
    });
  },
};
