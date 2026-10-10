import { httpClient } from "@/app/providers/http";
import type { StorageProvider, StorageBucket } from "../model/types";
const base = "/console/files";
export const filesApi = {
  async providers(signal?: AbortSignal): Promise<StorageProvider[]> {
    return (
      await httpClient.get<StorageProvider[]>(`${base}/providers/`, { signal })
    ).data;
  },
  async buckets(signal?: AbortSignal): Promise<StorageBucket[]> {
    return (
      await httpClient.get<StorageBucket[]>(`${base}/buckets/`, { signal })
    ).data;
  },
};
