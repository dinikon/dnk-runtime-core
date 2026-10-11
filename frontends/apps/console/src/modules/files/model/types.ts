export interface StorageProvider {
  id: string;
  name: string;
  kind: string;
  is_system: boolean;
}
export interface StorageBucket {
  id: string;
  provider_id: string;
  name: string;
  status: "preparing" | "ready" | "purged";
  files_count: number;
  size_bytes: number;
}
export const bucketStatusLabels = {
  preparing: "Подготавливается",
  ready: "Готов",
  purged: "Удалён",
};
export type FileCategory = "documents" | "images" | "videos" | "other";
export const categoryLabels: Record<FileCategory, string> = {
  documents: "Документы",
  images: "Изображения",
  videos: "Видео",
  other: "Другие",
};
export interface FileItem {
  file_id: string;
  bucket_id: string;
  bucket_name: string;
  provider_id: string;
  provider_name: string;
  name: string;
  content_type: string;
  category: FileCategory;
  size_bytes: number;
  created_at: string;
}
export interface TrashFileItem extends FileItem {
  status: "trashed" | "purging";
  deleted_at: string;
  purge_after: string;
  purge_requested_at: string | null;
}
export interface FilesPageResult {
  items: FileItem[];
  total: number;
  page: number;
  page_size: number;
}
export interface TrashPageResult {
  items: TrashFileItem[];
  total: number;
  page: number;
  page_size: number;
}
export interface FilesFilters {
  search: string;
  bucket_ids: string[];
  category?: FileCategory;
  page: number;
  page_size: number;
}
export interface FilesOverviewResult {
  active_count: number;
  active_size_bytes: number;
  trashed_count: number;
  trashed_size_bytes: number;
  pending_purge_count: number;
  pending_purge_size_bytes: number;
  categories: {
    category: FileCategory;
    files_count: number;
    size_bytes: number;
  }[];
}
export interface UploadFileResult {
  file_id: string;
  name: string;
  content_type: string;
  size_bytes: number;
}
export interface TrashFileResult {
  file_id: string;
  deleted_at: string;
  purge_after: string;
}
export interface RestoreFileResult {
  file_id: string;
  status: "ready";
}
export function formatStorageBytes(bytes: number): string {
  if (bytes <= 0) return "0 Б";
  const units = ["Б", "КиБ", "МиБ", "ГиБ", "ТиБ"];
  const index = Math.min(
    Math.floor(Math.log(bytes) / Math.log(1024)),
    units.length - 1,
  );
  return `${new Intl.NumberFormat("ru", { maximumFractionDigits: 1 }).format(bytes / 1024 ** index)} ${units[index]}`;
}
export function formatFileDate(value: string): string {
  return new Intl.DateTimeFormat("ru", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}
