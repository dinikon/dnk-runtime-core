import { httpClient } from "@/app/providers/http";
import type { SkuDto, CreateSkuDto } from "./contracts";
export const inventoryApi = {
  async listSkus(offset: number, signal?: AbortSignal) {
    return (
      await httpClient.get<SkuDto[]>("/console/inventory/skus", {
        params: { limit: 50, offset },
        signal,
      })
    ).data;
  },
  async getSku(id: string, signal?: AbortSignal) {
    return (
      await httpClient.get<SkuDto>(
        `/console/inventory/skus/${encodeURIComponent(id)}`,
        { signal },
      )
    ).data;
  },
  async createSku(payload: CreateSkuDto) {
    return (await httpClient.post<SkuDto>("/console/inventory/skus", payload))
      .data;
  },
};
