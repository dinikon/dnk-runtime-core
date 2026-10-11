import type { AxiosProgressEvent } from "axios";
import { httpClient } from "@/app/providers/http";
import type {
  StorageProvider,
  StorageBucket,
  FilesFilters,
  FilesPageResult,
  TrashPageResult,
  FilesOverviewResult,
  UploadFileResult,
  TrashFileResult,
  RestoreFileResult,
} from "../model/types";
const base = "/console/files";
function params(filters: FilesFilters): URLSearchParams {
  const result = new URLSearchParams({
    page: String(filters.page),
    page_size: String(filters.page_size),
  });
  if (filters.search) result.set("search", filters.search);
  if (filters.category) result.set("category", filters.category);
  filters.bucket_ids.forEach((id) => result.append("bucket_id", id));
  return result;
}
export const filesApi = {
  async preview(id: string, signal: AbortSignal): Promise<Blob> {
    return (
      await httpClient.get<Blob>(`${base}/items/${id}/preview/`, {
        signal,
        responseType: "blob",
        headers: { Accept: "*/*" },
      })
    ).data;
  },
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
  async list(
    filters: FilesFilters,
    signal: AbortSignal,
  ): Promise<FilesPageResult> {
    return (
      await httpClient.get<FilesPageResult>(`${base}/items/`, {
        params: params(filters),
        signal,
      })
    ).data;
  },
  async trashList(
    filters: FilesFilters,
    signal: AbortSignal,
  ): Promise<TrashPageResult> {
    return (
      await httpClient.get<TrashPageResult>(`${base}/trash/`, {
        params: params(filters),
        signal,
      })
    ).data;
  },
  async overview(
    ids: string[],
    signal: AbortSignal,
  ): Promise<FilesOverviewResult> {
    const query = new URLSearchParams();
    ids.forEach((id) => query.append("bucket_id", id));
    return (
      await httpClient.get<FilesOverviewResult>(`${base}/overview/`, {
        params: query,
        signal,
      })
    ).data;
  },
  async upload(
    file: File,
    bucketId: string,
    onProgress: (event: AxiosProgressEvent) => void,
    signal: AbortSignal,
  ): Promise<UploadFileResult> {
    const data = new FormData();
    data.append("file", file);
    data.append("bucket_id", bucketId);
    return (
      await httpClient.post<UploadFileResult>(`${base}/items/`, data, {
        headers: { "Content-Type": undefined },
        onUploadProgress: onProgress,
        signal,
      })
    ).data;
  },
  async trash(id: string, signal: AbortSignal): Promise<TrashFileResult> {
    return (
      await httpClient.delete<TrashFileResult>(`${base}/items/${id}/`, {
        signal,
      })
    ).data;
  },
  async restore(id: string, signal: AbortSignal): Promise<RestoreFileResult> {
    return (
      await httpClient.post<RestoreFileResult>(
        `${base}/items/${id}/restore/`,
        undefined,
        { signal },
      )
    ).data;
  },
  async purge(id: string, signal: AbortSignal): Promise<void> {
    await httpClient.delete(`${base}/trash/${id}/`, { signal });
  },
  async emptyTrash(
    signal: AbortSignal,
  ): Promise<{ job_id: string; cutoff: string }> {
    return (
      await httpClient.delete<{ job_id: string; cutoff: string }>(
        `${base}/trash/`,
        { signal },
      )
    ).data;
  },
};
