import { isAxiosError } from "axios";
import { httpClient } from "@/app/providers/http";
import { ChannelApiError } from "../model/channel.types";
import type {
  Channel,
  ChannelPage,
  ChannelFilters,
  Platform,
  ChannelSave,
  ChannelSaved,
} from "../model/channel.types";
import type {
  ChannelDto,
  ChannelPageDto,
  PlatformDto,
  SavedChannelDto,
} from "./channel.dto";
import {
  mapChannel,
  mapPlatform,
  mapSaved,
  createPayload,
  updatePayload,
} from "./channel.mapper";
async function safe<T>(request: () => Promise<T>): Promise<T> {
  try {
    return await request();
  } catch (error: unknown) {
    if (isAxiosError<{ detail?: { code?: string; field?: string } }>(error)) {
      throw new ChannelApiError(
        error.response?.data?.detail?.code ??
          (error.response?.status === 403 ? "access_denied" : "request_failed"),
        error.response?.status,
        error.response?.data?.detail?.field,
      );
    }
    throw error;
  }
}
const root = "/console/channels";
const item = (id: string): string => root + "/" + encodeURIComponent(id);
export const channelApi = {
  async platforms(signal?: AbortSignal): Promise<Platform[]> {
    return safe(async () =>
      (
        await httpClient.get<{ items: PlatformDto[] }>(root + "/platforms", {
          signal,
        })
      ).data.items.map(mapPlatform),
    );
  },
  async list(
    filters: ChannelFilters,
    signal?: AbortSignal,
  ): Promise<ChannelPage> {
    return safe(async () => {
      const { data } = await httpClient.get<ChannelPageDto>(root, {
        params: {
          search: filters.search,
          platform_kind: filters.platformKind || undefined,
          status: filters.status || undefined,
          offset: filters.offset,
          limit: 50,
        },
        signal,
      });
      return { ...data, items: data.items.map(mapChannel) };
    });
  },
  async get(id: string, signal?: AbortSignal): Promise<Channel> {
    return safe(async () =>
      mapChannel((await httpClient.get<ChannelDto>(item(id), { signal })).data),
    );
  },
  async create(
    value: ChannelSave,
    signal?: AbortSignal,
  ): Promise<ChannelSaved> {
    return safe(async () =>
      mapSaved(
        (
          await httpClient.post<SavedChannelDto>(root, createPayload(value), {
            signal,
          })
        ).data,
      ),
    );
  },
  async update(
    id: string,
    value: ChannelSave,
    revision: number,
    signal?: AbortSignal,
  ): Promise<ChannelSaved> {
    return safe(async () =>
      mapSaved(
        (
          await httpClient.patch<SavedChannelDto>(
            item(id),
            updatePayload(value, revision),
            { signal },
          )
        ).data,
      ),
    );
  },
  async verify(id: string, signal?: AbortSignal): Promise<ChannelSaved> {
    return safe(async () =>
      mapSaved(
        (
          await httpClient.post<SavedChannelDto>(
            item(id) + "/connection/verify",
            undefined,
            { signal },
          )
        ).data,
      ),
    );
  },
  async delete(
    id: string,
    revision: number,
    signal?: AbortSignal,
  ): Promise<void> {
    return safe(async () => {
      await httpClient.delete(item(id), {
        params: { expected_revision: revision },
        signal,
      });
    });
  },
};
