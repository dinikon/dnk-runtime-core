import type { FilesFilters } from "./types";
export const filesKeys = {
  tenant: (id: string) => ["files", id] as const,
  files: (id: string, filters: FilesFilters) =>
    ["files", id, "items", filters] as const,
  trash: (id: string, filters: FilesFilters) =>
    ["files", id, "trash", filters] as const,
  overview: (id: string, buckets: string[]) =>
    ["files", id, "overview", buckets] as const,
};
