import { httpClient } from "@/app/providers/http";
import type { GetFunnelDto, FunnelPageDto, SaveFunnelDto } from "./funnel.dto";
import {
  mapFunnel,
  mapFunnelDetails,
  mapSaveFunnel,
  funnelPayload,
} from "./funnel.mapper";
import type {
  Funnel,
  FunnelDetails,
  FunnelPage,
  FunnelDraft,
  SaveFunnelResult,
} from "../model/funnel.types";
export const funnelApi = {
  async list(
    modelKey?: string,
    search = "",
    offset = 0,
    signal?: AbortSignal,
  ): Promise<FunnelPage> {
    const { data } = await httpClient.get<FunnelPageDto>("/console/funnels", {
      params: { model_key: modelKey || undefined, search, offset, limit: 100 },
      signal,
    });
    return { ...data, items: data.items.map(mapFunnel) };
  },
  async options(modelKey: string, signal?: AbortSignal): Promise<Funnel[]> {
    const items = new Map<string, Funnel>();
    let offset = 0;
    while (true) {
      const page = await funnelApi.list(modelKey, "", offset, signal);
      for (const item of page.items) items.set(item.id, item);
      offset += page.items.length;
      if (offset >= page.total || !page.items.length) break;
    }
    return [...items.values()];
  },
  async get(id: string, signal?: AbortSignal): Promise<FunnelDetails> {
    return mapFunnelDetails(
      (
        await httpClient.get<GetFunnelDto>(
          "/console/funnels/" + encodeURIComponent(id),
          { signal },
        )
      ).data,
    );
  },
  async create(v: FunnelDraft): Promise<SaveFunnelResult> {
    return mapSaveFunnel(
      (
        await httpClient.post<SaveFunnelDto>("/console/funnels", {
          ...funnelPayload(v),
          model_key: v.modelKey,
        })
      ).data,
    );
  },
  async update(
    id: string,
    v: FunnelDraft,
    revision: number,
  ): Promise<SaveFunnelResult> {
    return mapSaveFunnel(
      (
        await httpClient.put<SaveFunnelDto>(
          "/console/funnels/" + encodeURIComponent(id),
          { ...funnelPayload(v), expected_revision: revision },
        )
      ).data,
    );
  },
};
